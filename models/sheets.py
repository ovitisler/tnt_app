import json
import os
import threading
import time

import gspread
from gspread.exceptions import APIError
from oauth2client.service_account import ServiceAccountCredentials

from models.cache import CacheManager
from models.metrics import log_api_call, log_rate_limit_error, log_cache_invalidation, get_metrics as _get_metrics
from models.test_mode import get_simulate_rate_limit

# Sheet name constants (single source of truth)
SCHEDULE_SHEET = 'Schedule'
ATTENDANCE_SCHEDULE_SHEET = 'Attendance Schedule'
MASTER_ROSTER_SHEET = 'Master Roster'
WEEKLY_TOTALS_SHEET = 'Weekly Totals'
WEEKLY_ATTENDANCE_TOTALS_SHEET = 'Weekly Attendance Totals'
COMPLETED_SECTIONS_SHEET = 'Completed Sections RAW'
ATTENDANCE_ENTRIES_SHEET = 'Attendance Entries RAW'

# Cache configuration - tiered TTLs based on how often data changes
CACHE_TTL_STATIC = 86400    # 1 day - sheets that rarely change
CACHE_TTL_DYNAMIC = 30     # 2 min - sheets that change with writes

# Stale-while-revalidate config
REFRESH_DEBOUNCE_SECONDS = 5  # Don't refresh if we refreshed within this window
_pending_refreshes = set()    # Sheets currently being refreshed in background
_refresh_lock = threading.Lock()

# Static sheets - only change when admin updates them (monthly or less)
STATIC_SHEETS = [
    SCHEDULE_SHEET,
    ATTENDANCE_SCHEDULE_SHEET,
    MASTER_ROSTER_SHEET,
]

# Sheets to invalidate when writing to RAW sheets
# RAW sheets trigger Totals recalculation
INVALIDATION_MAP = {
    COMPLETED_SECTIONS_SHEET: [COMPLETED_SECTIONS_SHEET, WEEKLY_TOTALS_SHEET],
    ATTENDANCE_ENTRIES_SHEET: [ATTENDANCE_ENTRIES_SHEET, WEEKLY_ATTENDANCE_TOTALS_SHEET],
}

def _get_ttl_for_sheet(sheet_name):
    """Get the appropriate TTL for a sheet based on how often it changes"""
    if sheet_name in STATIC_SHEETS:
        return CACHE_TTL_STATIC
    return CACHE_TTL_DYNAMIC

# Cache manager instance
_cache = CacheManager()


def _refresh_sheet_background(sheet_name):
    """Background task to refresh a sheet's cache"""
    refresh_started = time.time()
    try:
        spreadsheet = _get_spreadsheet_instance()
        data = spreadsheet.worksheet(sheet_name).get_all_records()
        size_bytes = len(json.dumps(data).encode('utf-8'))

        # Only update cache if it hasn't been modified (by write-through) since we started
        cached = _cache.get(sheet_name)
        if cached and cached.timestamp > refresh_started:
            print(f"[SHEETS] 🚫 Background refresh skipped for '{sheet_name}' - cache was updated during refresh")
        else:
            _cache.set(sheet_name, data, size_bytes)
            log_api_call('read', sheet_name, size_bytes, source='google-bg')
    except APIError as e:
        if e.response.status_code == 429:
            log_rate_limit_error(sheet_name)
        else:
            print(f"[SHEETS] ❌ Background refresh failed for '{sheet_name}': {e}")
    except Exception as e:
        print(f"[SHEETS] ❌ Background refresh failed for '{sheet_name}': {e}")
    finally:
        with _refresh_lock:
            _pending_refreshes.discard(sheet_name)


def _trigger_background_refresh(sheet_name):
    """Trigger a background refresh if not already pending and not recently refreshed"""
    with _refresh_lock:
        # Already refreshing this sheet?
        if sheet_name in _pending_refreshes:
            return False

        # Recently refreshed? (debounce)
        cached = _cache.get(sheet_name)
        if cached and cached.age() < REFRESH_DEBOUNCE_SECONDS:
            return False

        # Mark as pending and start refresh
        _pending_refreshes.add(sheet_name)

    thread = threading.Thread(target=_refresh_sheet_background, args=(sheet_name,), daemon=True)
    thread.start()
    print(f"[SHEETS] 🔄 Background refresh triggered for '{sheet_name}'")
    return True

class RateLimitError(Exception):
    """Raised when Google Sheets API rate limit is hit"""
    def __init__(self, message="Google Sheets rate limit exceeded. Please wait a moment and try again."):
        self.message = message
        super().__init__(self.message)

def get_google_creds():
    """Get Google credentials either from file or environment variable"""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    if 'GOOGLE_SHEETS_CREDS' in os.environ:
        creds_dict = json.loads(os.environ['GOOGLE_SHEETS_CREDS'])
        return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        return ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)

def get_spreadsheet():
    """Get the Google Sheets spreadsheet"""
    creds = get_google_creds()
    client = gspread.authorize(creds)
    sheet_name = os.environ.get('SHEET_NAME', 'TNT_App_Data')
    return client.open(sheet_name)

_spreadsheet = None

def _get_spreadsheet_instance():
    """Get or create the spreadsheet singleton"""
    global _spreadsheet
    if _spreadsheet is None:
        _spreadsheet = get_spreadsheet()
    return _spreadsheet

def get_sheet_data(sheet_name):
    """
    Get data from any sheet using stale-while-revalidate pattern.
    - Always returns cached data immediately if available (even if stale)
    - Triggers background refresh if cache is expired
    - Only fetches synchronously on cold start (no cache at all)
    """
    # Check for simulated rate limit (for testing)
    if get_simulate_rate_limit():
        log_rate_limit_error(sheet_name, simulated=True)
        raise RateLimitError()

    # Check if we have cached data
    cached = _cache.get(sheet_name)
    if cached:
        ttl = _get_ttl_for_sheet(sheet_name)

        if cached.is_fresh(ttl):
            # Fresh cache - return immediately
            log_api_call('read', sheet_name, cached.size_bytes, source='cache')
            return cached.data
        else:
            # Stale cache - return stale data, trigger background refresh
            log_api_call('read', sheet_name, cached.size_bytes, source='cache-stale')
            _trigger_background_refresh(sheet_name)
            return cached.data

    # Cold start - no cache at all, must fetch synchronously
    try:
        spreadsheet = _get_spreadsheet_instance()
        data = spreadsheet.worksheet(sheet_name).get_all_records()
    except APIError as e:
        if e.response.status_code == 429:
            log_rate_limit_error(sheet_name)
            raise RateLimitError()
        raise

    size_bytes = len(json.dumps(data).encode('utf-8'))

    # Store in cache
    _cache.set(sheet_name, data, size_bytes)

    log_api_call('read', sheet_name, size_bytes, source='google')
    return data

def get_worksheet(sheet_name):
    """Get a worksheet for direct operations (writes, updates)"""
    log_api_call('write', sheet_name, source='google')
    spreadsheet = _get_spreadsheet_instance()
    return spreadsheet.worksheet(sheet_name)


def cache_append_row(sheet_name, row_dict):
    """Update cache after appending a row (write-through)"""
    _cache.append_row(sheet_name, row_dict)


def cache_update_row(sheet_name, match_fn, updates):
    """
    Update cache after modifying a row (write-through).
    match_fn: function that takes a row dict and returns True if it's the row to update
    updates: dict of field_name -> new_value
    """
    return _cache.update_row(sheet_name, match_fn, updates)


def refresh_computed_sheets(sheet_name):
    """Trigger background refresh for computed sheets (Totals) after writing to RAW sheets"""
    if sheet_name in INVALIDATION_MAP:
        for related_sheet in INVALIDATION_MAP[sheet_name]:
            if related_sheet != sheet_name:
                _trigger_background_refresh(related_sheet)

def invalidate_cache(sheet_name=None):
    """Manually invalidate cache. If no sheet_name, invalidates all."""
    _cache.invalidate(sheet_name)
    log_cache_invalidation(sheet_name)

def get_metrics():
    """Get current metrics including cache state"""
    cache_info = {}
    for sheet_name, cached in _cache.items():
        ttl = _get_ttl_for_sheet(sheet_name)
        cache_info[sheet_name] = {
            'age_seconds': int(cached.age()),
            'ttl_seconds': ttl,
            'expires_in': int(ttl - cached.age()),
            'type': 'static' if sheet_name in STATIC_SHEETS else 'dynamic'
        }

    metrics = _get_metrics(
        cache_keys=_cache.keys(),
        simulate_rate_limit=get_simulate_rate_limit()
    )
    metrics['cache_details'] = cache_info
    metrics['ttl_static'] = CACHE_TTL_STATIC
    metrics['ttl_dynamic'] = CACHE_TTL_DYNAMIC
    return metrics
