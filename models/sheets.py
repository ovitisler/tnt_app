import json
import os
import threading
import time

import gspread
from gspread.exceptions import APIError
from oauth2client.service_account import ServiceAccountCredentials

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

# Cache storage: {sheet_name: {'data': [...], 'time': timestamp, 'size_bytes': int}}
_cache = {}


def _refresh_sheet_background(sheet_name):
    """Background task to refresh a sheet's cache"""
    refresh_started = time.time()
    try:
        spreadsheet = _get_spreadsheet_instance()
        data = spreadsheet.worksheet(sheet_name).get_all_records()
        size_bytes = len(json.dumps(data).encode('utf-8'))

        # Only update cache if it hasn't been modified (by write-through) since we started
        if sheet_name in _cache and _cache[sheet_name]['time'] > refresh_started:
            print(f"[SHEETS] 🚫 Background refresh skipped for '{sheet_name}' - cache was updated during refresh")
        else:
            _cache[sheet_name] = {
                'data': data,
                'time': time.time(),
                'size_bytes': size_bytes
            }
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
        if sheet_name in _cache:
            age = time.time() - _cache[sheet_name]['time']
            if age < REFRESH_DEBOUNCE_SECONDS:
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
    now = time.time()

    # Check for simulated rate limit (for testing)
    if get_simulate_rate_limit():
        log_rate_limit_error(sheet_name, simulated=True)
        raise RateLimitError()

    # Check if we have cached data
    if sheet_name in _cache:
        cached = _cache[sheet_name]
        age = now - cached['time']
        ttl = _get_ttl_for_sheet(sheet_name)

        if age < ttl:
            # Fresh cache - return immediately
            log_api_call('read', sheet_name, cached['size_bytes'], source='cache')
            return cached['data']
        else:
            # Stale cache - return stale data, trigger background refresh
            log_api_call('read', sheet_name, cached['size_bytes'], source='cache-stale')
            _trigger_background_refresh(sheet_name)
            return cached['data']

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
    _cache[sheet_name] = {
        'data': data,
        'time': now,
        'size_bytes': size_bytes
    }

    log_api_call('read', sheet_name, size_bytes, source='google')
    return data

def get_worksheet(sheet_name):
    """Get a worksheet for direct operations (writes, updates)"""
    log_api_call('write', sheet_name, source='google')
    spreadsheet = _get_spreadsheet_instance()
    return spreadsheet.worksheet(sheet_name)


def cache_append_row(sheet_name, row_dict):
    """Update cache after appending a row (write-through)"""
    if sheet_name in _cache:
        _cache[sheet_name]['data'].append(row_dict)
        _cache[sheet_name]['size_bytes'] += len(json.dumps(row_dict).encode('utf-8'))
        _cache[sheet_name]['time'] = time.time()  # Mark as fresh to prevent background refresh overwriting
        print(f"[SHEETS] 📝 Cache updated for '{sheet_name}' (append)")
    else:
        print(f"[SHEETS] ⚠️ No cache for '{sheet_name}' - write-through skipped")


def cache_update_row(sheet_name, match_fn, updates):
    """
    Update cache after modifying a row (write-through).
    match_fn: function that takes a row dict and returns True if it's the row to update
    updates: dict of field_name -> new_value
    """
    if sheet_name in _cache:
        for row in _cache[sheet_name]['data']:
            if match_fn(row):
                row.update(updates)
                _cache[sheet_name]['time'] = time.time()  # Mark as fresh to prevent background refresh overwriting
                print(f"[SHEETS] 📝 Cache updated for '{sheet_name}' (update)")
                return True
        print(f"[SHEETS] ⚠️ No matching row found in cache for '{sheet_name}'")
    else:
        print(f"[SHEETS] ⚠️ No cache for '{sheet_name}' - write-through skipped")
    return False


def refresh_computed_sheets(sheet_name):
    """Trigger background refresh for computed sheets (Totals) after writing to RAW sheets"""
    if sheet_name in INVALIDATION_MAP:
        for related_sheet in INVALIDATION_MAP[sheet_name]:
            if related_sheet != sheet_name:
                _trigger_background_refresh(related_sheet)

def invalidate_cache(sheet_name=None):
    """Manually invalidate cache. If no sheet_name, invalidates all."""
    global _cache
    if sheet_name:
        if sheet_name in _cache:
            del _cache[sheet_name]
            log_cache_invalidation(sheet_name)
    else:
        _cache = {}
        log_cache_invalidation()

def get_metrics():
    """Get current metrics including cache state"""
    now = time.time()
    cache_info = {}
    for sheet_name, cached in _cache.items():
        age = now - cached['time']
        ttl = _get_ttl_for_sheet(sheet_name)
        cache_info[sheet_name] = {
            'age_seconds': int(age),
            'ttl_seconds': ttl,
            'expires_in': int(ttl - age),
            'type': 'static' if sheet_name in STATIC_SHEETS else 'dynamic'
        }

    metrics = _get_metrics(
        cache_keys=list(_cache.keys()),
        simulate_rate_limit=get_simulate_rate_limit()
    )
    metrics['cache_details'] = cache_info
    metrics['ttl_static'] = CACHE_TTL_STATIC
    metrics['ttl_dynamic'] = CACHE_TTL_DYNAMIC
    return metrics
