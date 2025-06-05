from flask import Flask, render_template, request, redirect, url_for
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
    return redirect(url_for('roster'))

@app.route('/roster')
def roster():
    # Get all students from the roster sheet
    students = roster_sheet.get_all_records()
    # Get team data for the dropdown
    teams_data = teams_sheet.get_all_records()
    team_names = [team['Team'] for team in teams_data]
    
    # Organize students by team
    students_by_team = defaultdict(list)
    for student in students:
        team = student.get('Group', student.get('Team', 'Unassigned'))
        students_by_team[team].append(student)
    
    # Sort teams and students within teams
    sorted_students_by_team = {}
    for team in sorted(students_by_team.keys()):
        sorted_students_by_team[team] = sorted(students_by_team[team], key=lambda x: x['Name'])
    
    return render_template('roster.html', students_by_team=sorted_students_by_team, teams=team_names)

@app.route('/dashboard')
def dashboard():
    # Get all data from roster sheet
    students = roster_sheet.get_all_records()
    teams_data = teams_sheet.get_all_records()
    
    # Create teams dictionary with colors
    teams = {}
    for team in teams_data:
        teams[team['Team']] = {
            'color': team['Color'],
            'points': 0,
            'members': []
        }
    
    # Populate teams with student data
    for student in students:
        team_name = student.get('Group', student.get('Team', ''))  # Try Group first, then Team
        if team_name in teams:
            teams[team_name]['members'].append({
                'name': student['Name'],
                'sections_completed': student.get('Sections_Completed', 0),
                'points': student.get('Points', 0)
            })
            teams[team_name]['points'] += student.get('Points', 0)
    
    return render_template('dashboard.html', teams=teams)

@app.route('/add_student', methods=['POST'])
def add_student():
    name = request.form['name']
    team = request.form['team']
    
    # Find the column indices
    name_col = find_column_index(roster_sheet, 'Name')
    group_col = find_column_index(roster_sheet, 'Group')
    sections_col = find_column_index(roster_sheet, 'Sections_Completed')
    points_col = find_column_index(roster_sheet, 'Points')
    
    # Create a row with empty values
    row = [''] * len(roster_sheet.row_values(1))  # Create empty row matching header length
    
    # Fill in the values we care about
    if name_col: row[name_col-1] = name
    if group_col: row[group_col-1] = team
    if sections_col: row[sections_col-1] = 0
    if points_col: row[points_col-1] = 0
    
    # Add new student to roster sheet
    roster_sheet.append_row(row)
    
    return redirect(url_for('roster'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)

# Create templates/home.html with this content:
"""
<!DOCTYPE html>
<html>
<head>
    <title>Reading Teams Tracker</title>
    <style>
        .team-card {
            border: 1px solid #ccc;
            margin: 10px;
            padding: 15px;
            border-radius: 5px;
        }
        .team-points {
            font-size: 24px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <h1>Reading Teams Tracker</h1>
    
    <h2>Add Points</h2>
    <form action="/add_points" method="POST">
        <input type="text" name="student_name" placeholder="Student Name" required>
        <input type="number" name="sections" placeholder="Sections Completed" required>
        <button type="submit">Add Points</button>
    </form>

    <h2>Add New Student</h2>
    <form action="/add_student" method="POST">
        <input type="text" name="name" placeholder="Student Name" required>
        <input type="text" name="team" placeholder="Team Name" required>
        <button type="submit">Add Student</button>
    </form>

    <h2>Team Standings</h2>
    {% for team_name, team in teams.items() %}
    <div class="team-card">
        <h3>{{ team_name }}</h3>
        <p class="team-points">Total Points: {{ team['points'] }}</p>
        <h4>Team Members:</h4>
        <ul>
        {% for member in team['members'] %}
            <li>{{ member['name'] }} - {{ member['sections_completed'] }} sections completed ({{ member['points'] }} points)</li>
        {% endfor %}
        </ul>
    </div>
    {% endfor %}
</body>
</html>
"""
