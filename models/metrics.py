import time
from datetime import datetime
from collections import deque

# Metrics storage
_metrics = {
    'total_reads': 0,
    'total_writes': 0,
    'total_bytes': 0,
    'cache_hits': 0,
    'cache_misses': 0,
    'rate_limit_errors': 0,
    'recent_calls': deque(maxlen=100),
}

def _format_bytes(num_bytes):
    """Format bytes as human-readable string"""
    if num_bytes < 1024:
        return f"{num_bytes}B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f}KB"
    else:
        return f"{num_bytes / (1024 * 1024):.2f}MB"

def log_api_call(operation, sheet_name, size_bytes=None, source='google'):
    """Log an API call for metrics. source is 'google' or 'cache'"""
    now = time.time()
    call_record = {
        'time': now,
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'operation': operation,
        'sheet': sheet_name,
        'size_bytes': size_bytes,
        'source': source
    }
    _metrics['recent_calls'].append(call_record)

    if source == 'cache':
        _metrics['cache_hits'] += 1
    elif operation == 'read':
        _metrics['cache_misses'] += 1
        _metrics['total_reads'] += 1
        if size_bytes:
            _metrics['total_bytes'] += size_bytes
    else:
        _metrics['total_writes'] += 1

    # Calculate stats for last minute
    one_min_ago = now - 60
    calls_last_min = [c for c in _metrics['recent_calls'] if c['time'] > one_min_ago]
    google_calls = sum(1 for c in calls_last_min if c['source'] == 'google')
    cache_calls = sum(1 for c in calls_last_min if c['source'] == 'cache')

    size_str = f" | Size: {_format_bytes(size_bytes)}" if size_bytes else ""
    source_icon = "⚡CACHE" if source == 'cache' else "🌐GOOGLE"
    print(f"[SHEETS] {source_icon} {operation.upper()} '{sheet_name}'{size_str} | "
          f"Last 60s: {google_calls} google / {cache_calls} cache | "
          f"Total: {_metrics['cache_hits']} hits / {_metrics['cache_misses']} misses")

def log_rate_limit_error(sheet_name, simulated=False):
    """Log a rate limit error"""
    _metrics['rate_limit_errors'] += 1
    prefix = "SIMULATED " if simulated else ""
    print(f"[SHEETS] ⛔ {prefix}RATE LIMIT for '{sheet_name}'")

def log_cache_invalidation(sheet_name=None):
    """Log cache invalidation"""
    if sheet_name:
        print(f"[SHEETS] 🗑️ Cache invalidated for '{sheet_name}'")
    else:
        print("[SHEETS] 🗑️ All cache invalidated")

def get_metrics(cache_keys=None, simulate_rate_limit=False):
    """Get current API metrics"""
    now = time.time()
    one_min_ago = now - 60
    calls_last_min = [c for c in _metrics['recent_calls'] if c['time'] > one_min_ago]
    google_calls_last_min = [c for c in calls_last_min if c['source'] == 'google']
    cache_calls_last_min = [c for c in calls_last_min if c['source'] == 'cache']
    bytes_last_min = sum(c.get('size_bytes') or 0 for c in google_calls_last_min)

    total_requests = _metrics['cache_hits'] + _metrics['cache_misses']
    hit_rate = (_metrics['cache_hits'] / total_requests * 100) if total_requests > 0 else 0

    return {
        'total_google_reads': _metrics['total_reads'],
        'total_writes': _metrics['total_writes'],
        'total_bytes': _metrics['total_bytes'],
        'total_bytes_formatted': _format_bytes(_metrics['total_bytes']),
        'cache_hits': _metrics['cache_hits'],
        'cache_misses': _metrics['cache_misses'],
        'cache_hit_rate': f"{hit_rate:.1f}%",
        'rate_limit_errors': _metrics['rate_limit_errors'],
        'simulate_rate_limit': simulate_rate_limit,
        'google_calls_last_minute': len(google_calls_last_min),
        'cache_hits_last_minute': len(cache_calls_last_min),
        'bytes_last_minute': bytes_last_min,
        'bytes_last_minute_formatted': _format_bytes(bytes_last_min),
        'cached_sheets': cache_keys or [],
        'recent_calls': list(calls_last_min)
    }
