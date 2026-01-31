from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
from collections import defaultdict
from urllib.parse import unquote

from models.sheets import get_metrics
from models.utils import date_to_url
from routes.home import register_home_routes
from routes.attendance import register_attendance_routes
from routes.progress import register_progress_routes

app = Flask(__name__)

# Add template filters
app.jinja_env.filters['date_to_url'] = date_to_url

# Register route modules
register_home_routes(app)
register_attendance_routes(app)
register_progress_routes(app)

@app.route('/static/<path:filename>')
def static_files(filename):
    return app.send_static_file(filename)

@app.route('/metrics')
def metrics():
    return jsonify(get_metrics())

if __name__ == '__main__':
    app.run(debug=True, port=5001)
