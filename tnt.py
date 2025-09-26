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

def dates_match(date1, date2):
    """Check if two dates match, handling different formats"""
    if not date1 or not date2:
        return False
    
    try:
        # Parse ISO format (2025-09-17T00:00:00.000Z)
        if 'T' in str(date1):
            parsed_date1 = datetime.fromisoformat(str(date1).replace('Z', '+00:00')).date()
        else:
            # Parse readable format (September 17, 2025)
            parsed_date1 = datetime.strptime(str(date1), '%B %d, %Y').date()
        
        if 'T' in str(date2):
            parsed_date2 = datetime.fromisoformat(str(date2).replace('Z', '+00:00')).date()
        else:
            parsed_date2 = datetime.strptime(str(date2), '%B %d, %Y').date()
        
        return parsed_date1 == parsed_date2
    except:
        return str(date1) == str(date2)

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
            
            # Get weekly attendance totals for this date
            weekly_totals_sheet = spreadsheet.worksheet('Weekly Attendance Totals')
            all_totals = weekly_totals_sheet.get_all_records()
            
            # Filter totals by matching date
            date_totals = [row for row in all_totals if row.get('Date') == day_data.get('Date')]
            
            return render_template('attendance_details.html', 
                                 day_data=day_data, 
                                 day_index=day_index,
                                 weekly_totals=date_totals)
        else:
            return redirect(url_for('attendance'))
    except Exception as e:
        return redirect(url_for('attendance'))

@app.route('/attendance/<int:day_index>/team/<team_name>')
def team_attendance_details(day_index, team_name):
    # Get team attendance details for specific day and team
    try:
        attendance_schedule_sheet = spreadsheet.worksheet('Attendance Schedule')
        schedule_data = attendance_schedule_sheet.get_all_records()
        
        if 0 <= day_index < len(schedule_data):
            day_data = schedule_data[day_index]
            
            # Get weekly attendance totals for this date and team
            weekly_totals_sheet = spreadsheet.worksheet('Weekly Attendance Totals')
            all_totals = weekly_totals_sheet.get_all_records()
            
            # Find the specific team data
            team_data = next((row for row in all_totals 
                            if row.get('Date') == day_data.get('Date') 
                            and row.get('Team', '').lower() == team_name.lower()), None)
            
            # Get attendance entries for this date and team
            attendance_entries_sheet = spreadsheet.worksheet('Attendance Entries RAW')
            all_entries = attendance_entries_sheet.get_all_records()
            
            # Filter entries by date and team using flexible date matching
            checked_in_kids = [entry for entry in all_entries 
                             if dates_match(entry.get('Date'), day_data.get('Date')) 
                             and entry.get('Team', '').lower() == team_name.lower()]
            
            return render_template('team_attendance_details.html', 
                                 day_data=day_data, 
                                 day_index=day_index,
                                 team_data=team_data,
                                 team_name=team_name,
                                 checked_in_kids=checked_in_kids)
        else:
            return redirect(url_for('attendance'))
    except Exception as e:
        return redirect(url_for('attendance'))

@app.route('/attendance/<int:day_index>/team/<team_name>/kid/<kid_name>')
def kid_attendance_details(day_index, team_name, kid_name):
    # Get individual kid attendance details
    try:
        attendance_schedule_sheet = spreadsheet.worksheet('Attendance Schedule')
        schedule_data = attendance_schedule_sheet.get_all_records()
        
        if 0 <= day_index < len(schedule_data):
            day_data = schedule_data[day_index]
            
            # Get attendance entries for this specific kid, date, and team
            attendance_entries_sheet = spreadsheet.worksheet('Attendance Entries RAW')
            all_entries = attendance_entries_sheet.get_all_records()
            
            # Find the specific kid's entry
            kid_entry = next((entry for entry in all_entries 
                            if dates_match(entry.get('Date'), day_data.get('Date')) 
                            and entry.get('Team', '').lower() == team_name.lower()
                            and entry.get('Name', '').lower() == kid_name.lower()), None)
            
            return render_template('kid_attendance_details.html', 
                                 day_data=day_data, 
                                 day_index=day_index,
                                 team_name=team_name,
                                 kid_name=kid_name,
                                 kid_entry=kid_entry)
        else:
            return redirect(url_for('attendance'))
    except Exception as e:
        return redirect(url_for('attendance'))

@app.route('/progress')
def progress():
    return render_template('progress.html')





if __name__ == '__main__':
    app.run(debug=True, port=5001)
