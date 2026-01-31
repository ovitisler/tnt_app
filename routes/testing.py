import random
from datetime import datetime

from flask import jsonify, request

from models.metrics import reset_metrics
from models.sheets import (
    invalidate_cache,
    get_worksheet,
    COMPLETED_SECTIONS_SHEET,
    WEEKLY_TOTALS_SHEET,
    ATTENDANCE_ENTRIES_SHEET,
    WEEKLY_ATTENDANCE_TOTALS_SHEET,
)
from models.test_mode import set_simulate_rate_limit, get_simulate_rate_limit

# Test sheet config
LOAD_TEST_SHEET = 'Load Test Entries'

# Sheets to invalidate on test write (dynamic only, not static)
TEST_INVALIDATION_SHEETS = [
    COMPLETED_SECTIONS_SHEET,
    WEEKLY_TOTALS_SHEET,
    ATTENDANCE_ENTRIES_SHEET,
    WEEKLY_ATTENDANCE_TOTALS_SHEET,
]

# Test data for realistic write simulation
TEST_NAMES = ["Test Kid A", "Test Kid B", "Test Kid C", "Test Kid D", "Test Kid E"]
TEST_TEAMS = ["Red", "Blue", "Green", "Yellow"]
TEST_SECTIONS = ["1.1", "1.2", "1.3", "2.1", "2.2", "3.1"]

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

    @app.route('/test/reset')
    def test_reset():
        """Reset all metrics and clear cache - fresh start for testing"""
        reset_metrics()
        invalidate_cache()
        return jsonify({'message': 'Metrics reset and cache cleared'})

    @app.route('/test/write', methods=['POST'])
    def test_write():
        """
        Write a test row to the Load Test Entries sheet.
        Simulates real write behavior by invalidating only dynamic caches.
        """
        try:
            # Get data from request or generate random test data
            data = request.get_json() or {}
            name = data.get('name', random.choice(TEST_NAMES))
            team = data.get('team', random.choice(TEST_TEAMS))
            section = data.get('section', random.choice(TEST_SECTIONS))
            write_type = data.get('type', 'load_test')

            # Write to the test sheet
            worksheet = get_worksheet(LOAD_TEST_SHEET)
            row = [
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                name,
                team,
                datetime.now().strftime('%Y-%m-%d'),
                section,
                write_type
            ]
            worksheet.append_row(row, value_input_option='USER_ENTERED')

            # Invalidate only dynamic sheets (not static like Schedule, Roster)
            for sheet in TEST_INVALIDATION_SHEETS:
                invalidate_cache(sheet)

            return jsonify({
                'success': True,
                'message': 'Test row written and dynamic caches invalidated',
                'row': row
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/test/write/clear', methods=['POST'])
    def test_write_clear():
        """Clear all rows from the Load Test Entries sheet (except header)"""
        try:
            worksheet = get_worksheet(LOAD_TEST_SHEET)
            # Get all rows and delete all except header
            all_rows = worksheet.get_all_values()
            if len(all_rows) > 1:
                # Delete rows 2 to end (keep header)
                worksheet.delete_rows(2, len(all_rows))
            return jsonify({
                'success': True,
                'message': f'Cleared {len(all_rows) - 1} test rows'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
