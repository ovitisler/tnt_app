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
    # Get schedule data from the sheet
    try:
        schedule_sheet = spreadsheet.worksheet('Schedule')
        schedule_data = schedule_sheet.get_all_records()
        return render_template('home.html', schedule_data=schedule_data)
    except Exception as e:
        # If sheet doesn't exist or error occurs, return empty data
        return render_template('home.html', schedule_data=[], error=str(e))

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

@app.route('/edit_section', methods=['GET', 'POST'])
def edit_section():
    # Handle GET requests (redirect back)
    if request.method == 'GET':
        return redirect(url_for('home'))
    
    # Update section completion in Google Sheets
    try:
        day_index = int(request.form.get('day_index'))
        team_name = request.form.get('team_name')
        kid_name = request.form.get('kid_name')
        section_name = request.form.get('section_name')
        
        schedule_sheet = spreadsheet.worksheet('Schedule')
        schedule_data = schedule_sheet.get_all_records()
        
        if 0 <= day_index < len(schedule_data):
            day_data = schedule_data[day_index]
            
            # Get completed sections sheet
            completed_sections_sheet = spreadsheet.worksheet('Completed Sections RAW')
            all_sections = completed_sections_sheet.get_all_records()
            
            # Find the row to update
            for i, entry in enumerate(all_sections):
                if (dates_match(entry.get('Date'), day_data.get('Date')) 
                    and entry.get('Team', '').lower() == team_name.lower()
                    and entry.get('Name', '').lower() == kid_name.lower()
                    and str(entry.get('Section', '')) == str(section_name)):
                    
                    # Update the row with form data
                    row_num = i + 2  # +2 because sheets are 1-indexed and we skip header
                    
                    # Get headers to find column positions
                    headers = completed_sections_sheet.row_values(1)
                    
                    # Update all editable fields based on form state
                    protected_fields = ['day_index', 'team_name', 'kid_name', 'section_name', 'Name', 'Team', 'Date', 'Section', 'Timestamp', 'timestamp']
                    
                    for field_name in entry.keys():
                        if field_name not in protected_fields:
                            try:
                                col_index = headers.index(field_name) + 1
                                value = 'TRUE' if field_name in request.form else 'FALSE'
                                completed_sections_sheet.update_cell(row_num, col_index, value)
                            except ValueError:
                                continue
                    break
            
            return redirect(f'/home/{day_index}/team/{team_name}/kid/{kid_name}/section/{section_name}')
        
        return redirect(url_for('home'))
    except Exception as e:
        return redirect(url_for('home'))

@app.route('/attendance/<int:day_index>/team/<team_name>/checkin')
def checkin_form(day_index, team_name):
    try:
        # Get attendance schedule data
        attendance_schedule_sheet = spreadsheet.worksheet('Attendance Schedule')
        schedule_data = attendance_schedule_sheet.get_all_records()
        
        # Get team kids from Master Roster
        roster_sheet = spreadsheet.worksheet('Master Roster')
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

@app.route('/submit_section', methods=['POST'])
def submit_section():
    try:
        # Get form data
        name = request.form.get('name')
        date = request.form.get('date')
        team = request.form.get('team')
        day_index = request.form.get('day_index')
        section = request.form.get('section')
        
        # Get completed sections sheet and headers
        completed_sections_sheet = spreadsheet.worksheet('Completed Sections RAW')
        headers = completed_sections_sheet.row_values(1)
        
        # Create data mapping
        data_map = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Name': name,
            'Team': team,
            'Date': date,
            'Section': section,
            'Section Complete': True if 'Section Complete' in request.form else False,
            'Silver Credit': True if 'Silver Credit' in request.form else False,
            'Gold Credit': True if 'Gold Credit' in request.form else False
        }
        
        # Build row in correct order based on headers
        new_row = []
        for header in headers:
            new_row.append(data_map.get(header, ''))
        
        completed_sections_sheet.append_row(new_row, value_input_option='USER_ENTERED')
        
        return redirect(f'/home/{day_index}/team/{team}')
    except Exception as e:
        return redirect(url_for('home'))

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

@app.route('/home/<int:day_index>')
def home_details(day_index):
    # Get schedule data and show details for specific day
    try:
        schedule_sheet = spreadsheet.worksheet('Schedule')
        schedule_data = schedule_sheet.get_all_records()
        
        if 0 <= day_index < len(schedule_data):
            day_data = schedule_data[day_index]
            
            # Get weekly totals for this date
            weekly_totals_sheet = spreadsheet.worksheet('Weekly Totals')
            all_totals = weekly_totals_sheet.get_all_records()
            
            # Filter totals by matching date
            date_totals = [row for row in all_totals if row.get('Date') == day_data.get('Date')]
            
            return render_template('home_details.html', 
                                 day_data=day_data, 
                                 day_index=day_index,
                                 weekly_totals=date_totals)
        else:
            return redirect(url_for('home'))
    except Exception as e:
        return redirect(url_for('home'))

@app.route('/home/<int:day_index>/team/<team_name>')
def home_team_details(day_index, team_name):
    # Get team details for specific day and team from home perspective
    try:
        schedule_sheet = spreadsheet.worksheet('Schedule')
        schedule_data = schedule_sheet.get_all_records()
        
        if 0 <= day_index < len(schedule_data):
            day_data = schedule_data[day_index]
            
            # Get weekly totals for this date and team
            weekly_totals_sheet = spreadsheet.worksheet('Weekly Totals')
            all_totals = weekly_totals_sheet.get_all_records()
            
            # Find the specific team data
            team_data = next((row for row in all_totals 
                            if row.get('Date') == day_data.get('Date') 
                            and row.get('Team', '').lower() == team_name.lower()), None)
            
            # Get completed sections for this date and team
            completed_sections_sheet = spreadsheet.worksheet('Completed Sections RAW')
            all_sections = completed_sections_sheet.get_all_records()
            
            # Filter sections by date and team using flexible date matching
            team_sections = [entry for entry in all_sections 
                           if dates_match(entry.get('Date'), day_data.get('Date')) 
                           and entry.get('Team', '').lower() == team_name.lower()]
            
            # Group sections by kid name
            kids_sections = defaultdict(list)
            for section in team_sections:
                kid_name = section.get('Name', '')
                if kid_name:
                    kids_sections[kid_name].append(section.get('Section', ''))
            
            return render_template('home_team_details.html', 
                                 day_data=day_data, 
                                 day_index=day_index,
                                 team_data=team_data,
                                 team_name=team_name,
                                 kids_sections=kids_sections)
        else:
            return redirect(url_for('home'))
    except Exception as e:
        return redirect(url_for('home'))

@app.route('/home/<int:day_index>/team/<team_name>/record_section')
def record_section_form(day_index, team_name):
    try:
        # Get schedule data
        schedule_sheet = spreadsheet.worksheet('Schedule')
        schedule_data = schedule_sheet.get_all_records()
        
        # Get team kids from Master Roster
        roster_sheet = spreadsheet.worksheet('Master Roster')
        roster_data = roster_sheet.get_all_records()
        team_kids = [row['Name'] for row in roster_data if row.get('Group', '').lower() == team_name.lower()]
        
        if 0 <= day_index < len(schedule_data):
            day_data = schedule_data[day_index]
            return render_template('record_section_form.html',
                                 day_data=day_data,
                                 day_index=day_index,
                                 team_name=team_name,
                                 team_kids=team_kids,
                                 schedule_data=schedule_data)
        else:
            return redirect(url_for('home'))
    except Exception as e:
        return redirect(url_for('home'))

@app.route('/home/<int:day_index>/team/<team_name>/kid/<path:kid_name>/section/<path:section_name>')
def home_section_details(day_index, team_name, kid_name, section_name):
    # Get section completion details
    try:
        schedule_sheet = spreadsheet.worksheet('Schedule')
        schedule_data = schedule_sheet.get_all_records()
        
        if 0 <= day_index < len(schedule_data):
            day_data = schedule_data[day_index]
            
            # Get completed sections for this specific entry
            completed_sections_sheet = spreadsheet.worksheet('Completed Sections RAW')
            all_sections = completed_sections_sheet.get_all_records()
            
            # Decode URL-encoded parameters
            kid_name = unquote(kid_name)
            section_name = unquote(section_name)
            
            # Find the specific section entry
            section_entry = next((entry for entry in all_sections 
                                if dates_match(entry.get('Date'), day_data.get('Date')) 
                                and entry.get('Team', '').lower() == team_name.lower()
                                and entry.get('Name', '').lower() == kid_name.lower()
                                and str(entry.get('Section', '')) == str(section_name)), None)
            
            return render_template('home_section_details.html', 
                                 day_data=day_data, 
                                 day_index=day_index,
                                 team_name=team_name,
                                 kid_name=kid_name,
                                 section_name=section_name,
                                 section_entry=section_entry)
        else:
            return redirect(url_for('home'))
    except Exception as e:
        print(f"Error in home_section_details: {e}")
        return redirect(url_for('home'))

@app.route('/progress')
def progress():
    try:
        # Get all students from Master Roster
        roster_sheet = spreadsheet.worksheet('Master Roster')
        roster_data = roster_sheet.get_all_records()
        
        return render_template('progress.html', students=roster_data)
    except Exception as e:
        return render_template('progress.html', students=[], error=str(e))

@app.route('/progress/student/<path:student_name>')
def student_progress(student_name):
    try:
        student_name = unquote(student_name)
        
        # Get student info from Master Roster
        roster_sheet = spreadsheet.worksheet('Master Roster')
        roster_data = roster_sheet.get_all_records()
        student_info = next((student for student in roster_data if student.get('Name', '').lower() == student_name.lower()), None)
        
        # Get all completed sections for this student
        completed_sections_sheet = spreadsheet.worksheet('Completed Sections RAW')
        all_sections = completed_sections_sheet.get_all_records()
        
        # Filter sections for this student
        student_sections = [section for section in all_sections if section.get('Name', '').lower() == student_name.lower()]
        
        # Calculate stats
        total_sections = len(student_sections)
        silver_earned = sum(1 for section in student_sections if section.get('Silver Credit', '').lower() in ['true', 'yes', '1'])
        gold_earned = sum(1 for section in student_sections if section.get('Gold Credit', '').lower() in ['true', 'yes', '1'])
        
        return render_template('student_progress.html',
                             student_name=student_name,
                             student_info=student_info,
                             student_sections=student_sections,
                             total_sections=total_sections,
                             silver_earned=silver_earned,
                             gold_earned=gold_earned)
    except Exception as e:
        return redirect(url_for('progress'))

@app.route('/progress/student/<path:student_name>/section/<int:section_index>')
def student_section_details(student_name, section_index):
    try:
        student_name = unquote(student_name)
        
        # Get all completed sections for this student
        completed_sections_sheet = spreadsheet.worksheet('Completed Sections RAW')
        all_sections = completed_sections_sheet.get_all_records()
        
        # Filter sections for this student
        student_sections = [section for section in all_sections if section.get('Name', '').lower() == student_name.lower()]
        
        if 0 <= section_index < len(student_sections):
            section_entry = student_sections[section_index]
            
            return render_template('student_section_details.html',
                                 student_name=student_name,
                                 section_entry=section_entry,
                                 section_index=section_index)
        else:
            return redirect(f'/progress/student/{student_name}')
    except Exception as e:
        return redirect(url_for('progress'))

@app.route('/edit_progress_section', methods=['GET', 'POST'])
def edit_progress_section():
    # Handle GET requests (redirect back)
    if request.method == 'GET':
        return redirect(url_for('progress'))
    
    # Update section completion in Google Sheets
    try:
        student_name = request.form.get('student_name')
        section_index = int(request.form.get('section_index'))
        
        # Get all completed sections for this student
        completed_sections_sheet = spreadsheet.worksheet('Completed Sections RAW')
        all_sections = completed_sections_sheet.get_all_records()
        
        # Filter sections for this student
        student_sections = [section for section in all_sections if section.get('Name', '').lower() == student_name.lower()]
        
        if 0 <= section_index < len(student_sections):
            target_section = student_sections[section_index]
            
            # Find the actual row in the sheet
            for i, entry in enumerate(all_sections):
                if (entry.get('Name', '').lower() == student_name.lower()
                    and entry.get('Date') == target_section.get('Date')
                    and str(entry.get('Section', '')) == str(target_section.get('Section', ''))):
                    
                    # Update the row with form data
                    row_num = i + 2  # +2 because sheets are 1-indexed and we skip header
                    
                    # Get headers to find column positions
                    headers = completed_sections_sheet.row_values(1)
                    
                    # Update all editable fields based on form state
                    protected_fields = ['student_name', 'section_index', 'Name', 'Team', 'Date', 'Section', 'Timestamp', 'timestamp']
                    
                    for field_name in entry.keys():
                        if field_name not in protected_fields:
                            try:
                                col_index = headers.index(field_name) + 1
                                value = 'TRUE' if field_name in request.form else 'FALSE'
                                completed_sections_sheet.update_cell(row_num, col_index, value)
                            except ValueError:
                                continue
                    break
            
            return redirect(f'/progress/student/{student_name}/section/{section_index}')
        
        return redirect(url_for('progress'))
    except Exception as e:
        return redirect(url_for('progress'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)
