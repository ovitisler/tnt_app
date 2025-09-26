from flask import Flask, render_template, request, redirect, url_for, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from collections import defaultdict
import os
import json

app = Flask(__name__)

def get_google_creds():
    """Get Google credentials either from file or environment variable"""
    if 'GOOGLE_SHEETS_CREDS' in os.environ:
        creds_dict = json.loads(os.environ['GOOGLE_SHEETS_CREDS'])
        return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        return ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)

# Setup Google Sheets connection
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
creds = get_google_creds()
client = gspread.authorize(creds)

# Open the Google Sheet
sheet_name = os.environ.get('SHEET_NAME', 'TNT_App_Data')
spreadsheet = client.open(sheet_name)
roster_sheet = spreadsheet.worksheet('Master Roster')
teams_sheet = spreadsheet.worksheet('Teams')

def find_column_index(worksheet, header_name):
    """Find the index of a column by its header name"""
    headers = worksheet.row_values(1)  # Get headers from first row
    try:
        return headers.index(header_name) + 1  # Convert to 1-based index
    except ValueError:
        return None

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/attendance')
def attendance():
    # Get attendance schedule data from the sheet
    try:
        attendance_schedule_sheet = spreadsheet.worksheet('Attendance Schedule')
        schedule_data = attendance_schedule_sheet.get_all_records()
        return render_template('attendance.html', schedule_data=schedule_data)
    except Exception as e:
        # If sheet doesn't exist or error occurs, return empty data
        return render_template('attendance.html', schedule_data=[], error=str(e))

@app.route('/attendance/<int:day_index>')
def attendance_details(day_index):
    # Get attendance schedule data and show details for specific day
    try:
        attendance_schedule_sheet = spreadsheet.worksheet('Attendance Schedule')
        schedule_data = attendance_schedule_sheet.get_all_records()
        
        if 0 <= day_index < len(schedule_data):
            day_data = schedule_data[day_index]
            return render_template('attendance_details.html', day_data=day_data, day_index=day_index)
        else:
            return redirect(url_for('attendance'))
    except Exception as e:
        return redirect(url_for('attendance'))

@app.route('/progress')
def progress():
    return render_template('progress.html')





if __name__ == '__main__':
    app.run(debug=True, port=5001)
