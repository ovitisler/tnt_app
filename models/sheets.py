import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import time
from datetime import datetime
from collections import deque

# Simple metrics tracking
_metrics = {
    'total_reads': 0,
    'total_writes': 0,
    'total_bytes': 0,
    'recent_calls': deque(maxlen=100),  # last 100 calls with timestamps
}

def _format_bytes(num_bytes):
    """Format bytes as human-readable string"""
    if num_bytes < 1024:
        return f"{num_bytes}B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f}KB"
    else:
        return f"{num_bytes / (1024 * 1024):.2f}MB"

def _log_api_call(operation, sheet_name, size_bytes=None):
    """Log an API call for metrics"""
    now = time.time()
    call_record = {
        'time': now,
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'operation': operation,
        'sheet': sheet_name,
        'size_bytes': size_bytes
    }
    _metrics['recent_calls'].append(call_record)

    if operation == 'read':
        _metrics['total_reads'] += 1
    else:
        _metrics['total_writes'] += 1

    if size_bytes:
        _metrics['total_bytes'] += size_bytes

    # Calculate calls in last minute
    one_min_ago = now - 60
    calls_last_min = sum(1 for c in _metrics['recent_calls'] if c['time'] > one_min_ago)

    size_str = f" | Size: {_format_bytes(size_bytes)}" if size_bytes else ""
    print(f"[SHEETS API] {operation.upper()} '{sheet_name}'{size_str} | "
          f"Last 60s: {calls_last_min} calls | "
          f"Total: {_metrics['total_reads']}R / {_metrics['total_writes']}W / {_format_bytes(_metrics['total_bytes'])}")

def get_metrics():
    """Get current API metrics"""
    now = time.time()
    one_min_ago = now - 60
    calls_last_min = [c for c in _metrics['recent_calls'] if c['time'] > one_min_ago]
    bytes_last_min = sum(c.get('size_bytes') or 0 for c in calls_last_min)
    return {
        'total_reads': _metrics['total_reads'],
        'total_writes': _metrics['total_writes'],
        'total_bytes': _metrics['total_bytes'],
        'total_bytes_formatted': _format_bytes(_metrics['total_bytes']),
        'calls_last_minute': len(calls_last_min),
        'bytes_last_minute': bytes_last_min,
        'bytes_last_minute_formatted': _format_bytes(bytes_last_min),
        'recent_calls': list(calls_last_min)
    }

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
    """Get data from any sheet"""
    spreadsheet = _get_spreadsheet_instance()
    data = spreadsheet.worksheet(sheet_name).get_all_records()
    size_bytes = len(json.dumps(data).encode('utf-8'))
    _log_api_call('read', sheet_name, size_bytes)
    return data

def get_worksheet(sheet_name):
    """Get a worksheet for direct operations (writes, updates)"""
    _log_api_call('write', sheet_name)
    spreadsheet = _get_spreadsheet_instance()
    return spreadsheet.worksheet(sheet_name)