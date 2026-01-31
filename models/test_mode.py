# Test mode controls for development/debugging

_simulate_rate_limit = False

def set_simulate_rate_limit(enabled):
    """Enable/disable simulated rate limit errors for testing"""
    global _simulate_rate_limit
    _simulate_rate_limit = enabled
    status = "ENABLED" if enabled else "DISABLED"
    print(f"[SHEETS] 🧪 Simulated rate limit {status}")
    return _simulate_rate_limit

def get_simulate_rate_limit():
    """Check if rate limit simulation is enabled"""
    return _simulate_rate_limit
