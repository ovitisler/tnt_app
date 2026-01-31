from flask import Flask, render_template, jsonify

from models.sheets import get_metrics, RateLimitError
from models.utils import date_to_url
from routes.home import register_home_routes
from routes.attendance import register_attendance_routes
from routes.progress import register_progress_routes
from routes.testing import register_testing_routes

app = Flask(__name__)

# Add template filters
app.jinja_env.filters['date_to_url'] = date_to_url

# Register route modules
register_home_routes(app)
register_attendance_routes(app)
register_progress_routes(app)
register_testing_routes(app)

@app.route('/static/<path:filename>')
def static_files(filename):
    return app.send_static_file(filename)

@app.route('/metrics')
def metrics():
    return jsonify(get_metrics())

@app.errorhandler(RateLimitError)
def handle_rate_limit_error(error):
    return render_template('error.html',
        error_title="Slow Down!",
        error_message="We're getting data too fast. Please wait a moment and try again.",
        error_details="Google Sheets API rate limit exceeded."
    ), 429

if __name__ == '__main__':
    app.run(debug=True, port=5001)
