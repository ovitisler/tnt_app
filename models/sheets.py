import gspread
from gspread.exceptions import APIError
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import time

from models.metrics import log_api_call, log_rate_limit_error, log_cache_invalidation, get_metrics as _get_metrics
from models.test_mode import get_simulate_rate_limit

# Cache configuration
CACHE_TTL_SECONDS = 30

# Cache storage: {sheet_name: {'data': [...], 'time': timestamp, 'size_bytes': int}}
_cache = {}

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
    """Get data from any sheet, with caching"""
    now = time.time()

    # Check for simulated rate limit (for testing)
    if get_simulate_rate_limit():
        log_rate_limit_error(sheet_name, simulated=True)
        raise RateLimitError()

    # Check cache
    if sheet_name in _cache:
        cached = _cache[sheet_name]
        age = now - cached['time']
        if age < CACHE_TTL_SECONDS:
            log_api_call('read', sheet_name, cached['size_bytes'], source='cache')
            return cached['data']

    # Cache miss - fetch from Google
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
    # Invalidate cache for this sheet since we're about to modify it
    if sheet_name in _cache:
        del _cache[sheet_name]
        log_cache_invalidation(sheet_name)
    spreadsheet = _get_spreadsheet_instance()
    return spreadsheet.worksheet(sheet_name)

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
    return _get_metrics(
        cache_keys=list(_cache.keys()),
        simulate_rate_limit=get_simulate_rate_limit()
    )
