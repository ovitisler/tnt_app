from flask import Flask, render_template, request, redirect, url_for, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from collections import defaultdict
import os
import json
from urllib.parse import unquote

app = Flask(__name__)

@app.route('/static/<path:filename>')
def static_files(filename):
    return app.send_static_file(filename)

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

@app.route('/attendance/<int:day_index>/team/<team_name>/kid/<path:kid_name>')
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

@app.route('/edit_attendance', methods=['GET', 'POST'])
def edit_kid_attendance():
    print(f"Request method: {request.method}")
    print(f"Form data: {request.form}")
    
    # Handle GET requests (redirect back)
    if request.method == 'GET':
        return redirect(url_for('attendance'))
    
    # Update kid attendance in Google Sheets
    try:
        day_index = int(request.form.get('day_index'))
        team_name = request.form.get('team_name')
        kid_name = request.form.get('kid_name')
        
        attendance_schedule_sheet = spreadsheet.worksheet('Attendance Schedule')
        schedule_data = attendance_schedule_sheet.get_all_records()
        
        if 0 <= day_index < len(schedule_data):
            day_data = schedule_data[day_index]
            
            # Get attendance entries sheet
            attendance_entries_sheet = spreadsheet.worksheet('Attendance Entries RAW')
            all_entries = attendance_entries_sheet.get_all_records()
            
            # Find the row to update
            for i, entry in enumerate(all_entries):
                if (dates_match(entry.get('Date'), day_data.get('Date')) 
                    and entry.get('Team', '').lower() == team_name.lower()
                    and entry.get('Name', '').lower() == kid_name.lower()):
                    
                    # Update the row with form data
                    row_num = i + 2  # +2 because sheets are 1-indexed and we skip header
                    
                    # Get headers to find column positions
                    headers = attendance_entries_sheet.row_values(1)
                    
                    # Update all editable fields based on form state
                    protected_fields = ['day_index', 'team_name', 'kid_name', 'Name', 'Team', 'Date', 'Timestamp', 'timestamp']
                    
                    for field_name in entry.keys():
                        if field_name not in protected_fields:
                            try:
                                col_index = headers.index(field_name) + 1
                                value = 'TRUE' if field_name in request.form else 'FALSE'
                                attendance_entries_sheet.update_cell(row_num, col_index, value)
                            except ValueError:
                                continue
                    break
            
            return redirect(f'/attendance/{day_index}/team/{team_name}/kid/{kid_name}')
        
        return redirect(url_for('attendance'))
    except Exception as e:
        return redirect(url_for('attendance'))

@app.route('/attendance/<int:day_index>/team/<team_name>/checkin')
def checkin_form(day_index, team_name):
    try:
        # Get attendance schedule data
        attendance_schedule_sheet = spreadsheet.worksheet('Attendance Schedule')
        schedule_data = attendance_schedule_sheet.get_all_records()
        
        # Get team kids from Master Roster
        roster_data = roster_sheet.get_all_records()
        team_kids = [row['Name'] for row in roster_data if row.get('Group', '').lower() == team_name.lower()]
        
        if 0 <= day_index < len(schedule_data):
            day_data = schedule_data[day_index]
            return render_template('checkin_form.html',
                                 day_data=day_data,
                                 day_index=day_index,
                                 team_name=team_name,
                                 team_kids=team_kids,
                                 schedule_data=schedule_data)
        else:
            return redirect(url_for('attendance'))
    except Exception as e:
        return redirect(url_for('attendance'))

@app.route('/submit_checkin', methods=['POST'])
def submit_checkin():
    try:
        # Get form data
        name = request.form.get('name')
        date = request.form.get('date')
        team = request.form.get('team')
        day_index = request.form.get('day_index')
        
        # Get attendance entries sheet and headers
        attendance_entries_sheet = spreadsheet.worksheet('Attendance Entries RAW')
        headers = attendance_entries_sheet.row_values(1)
        
        # Create data mapping
        data_map = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Name': name,
            'Team': team,
            'Date': date,
            'Present': True if 'present' in request.form else False,
            'Has Bible': True if 'has_bible' in request.form else False,
            'Wearing Shirt?': True if 'wearing_shirt' in request.form else False,
            'Has Book?': True if 'has_book' in request.form else False,
            'Did Homework?': True if 'did_homework' in request.form else False,
            'Has Dues?': True if 'has_dues' in request.form else False
        }
        
        # Build row in correct order based on headers
        new_row = []
        for header in headers:
            new_row.append(data_map.get(header, ''))
        
        attendance_entries_sheet.append_row(new_row, value_input_option='USER_ENTERED')
        
        return redirect(f'/attendance/{day_index}/team/{team}')
    except Exception as e:
        return redirect(url_for('attendance'))

@app.route('/progress')
def progress():
    return render_template('progress.html')

if __name__ == '__main__':
    app.run(debug=True, port=5001)
