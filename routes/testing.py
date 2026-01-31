from flask import jsonify

from models.test_mode import set_simulate_rate_limit, get_simulate_rate_limit
from models.sheets import invalidate_cache

def register_testing_routes(app):
    """Register test/debug routes (development only)"""

    @app.route('/test/rate-limit/on')
    def test_rate_limit_on():
        set_simulate_rate_limit(True)
        invalidate_cache()
        return jsonify({
            'simulate_rate_limit': True,
            'message': 'Rate limit simulation ENABLED. All requests will fail.'
        })

    @app.route('/test/rate-limit/off')
    def test_rate_limit_off():
        set_simulate_rate_limit(False)
        return jsonify({
            'simulate_rate_limit': False,
            'message': 'Rate limit simulation DISABLED. Normal operation resumed.'
        })

    @app.route('/test/rate-limit/status')
    def test_rate_limit_status():
        return jsonify({'simulate_rate_limit': get_simulate_rate_limit()})

    @app.route('/test/cache/clear')
    def test_cache_clear():
        invalidate_cache()
        return jsonify({'message': 'Cache cleared'})
