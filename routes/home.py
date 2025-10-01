from flask import render_template, request, redirect, url_for
from datetime import datetime
from collections import defaultdict
from urllib.parse import unquote

from models.sheets import get_spreadsheet
from models.utils import dates_match, find_day_by_date, date_to_url, url_to_date

# Sheet name constants
SCHEDULE_SHEET = 'Schedule'
WEEKLY_TOTALS_SHEET = 'Weekly Totals'
COMPLETED_SECTIONS_SHEET = 'Completed Sections RAW'
MASTER_ROSTER_SHEET = 'Master Roster'

# Get spreadsheet instance
spreadsheet = get_spreadsheet()

# Helper function
def get_sheet_data(sheet_name):
    """Get data from any sheet"""
    return spreadsheet.worksheet(sheet_name).get_all_records()

def register_home_routes(app):
    """Register all home-related routes"""
    
    @app.route('/')
    def home():
        # Get schedule data from the sheet
        try:
            schedule_data = get_sheet_data(SCHEDULE_SHEET)
            return render_template('home.html', schedule_data=schedule_data)
        except Exception as e:
            # If sheet doesn't exist or error occurs, return empty data
            return render_template('home.html', schedule_data=[], error=str(e))

    @app.route('/home/<date_str>')
    def home_details(date_str):
        # Get schedule data and show details for specific day
        try:
            schedule_data = get_sheet_data(SCHEDULE_SHEET)
            
            # Convert URL date back to display format for matching
            display_date = url_to_date(date_str)
            day_data = find_day_by_date(schedule_data, display_date)
            
            if day_data:
                # Get weekly totals for this date
                all_totals = get_sheet_data(WEEKLY_TOTALS_SHEET)
                
                # Filter totals by matching date
                date_totals = [row for row in all_totals if row.get('Date') == day_data.get('Date')]
                
                return render_template('home_details.html', 
                                     day_data=day_data, 
                                     date_str=date_str,
                                     weekly_totals=date_totals)
            else:
                return redirect(url_for('home'))
        except Exception as e:
            return redirect(url_for('home'))

    @app.route('/home/<date_str>/team/<team_name>')
    def home_team_details(date_str, team_name):
        # Get team details for specific day and team from home perspective
        try:
            schedule_data = get_sheet_data(SCHEDULE_SHEET)
            
            # Convert URL date back to display format for matching
            display_date = url_to_date(date_str)
            day_data = find_day_by_date(schedule_data, display_date)
            
            if day_data:
                # Get weekly totals for this date and team
                all_totals = get_sheet_data(WEEKLY_TOTALS_SHEET)
                
                # Find the specific team data
                team_data = next((row for row in all_totals 
                                if row.get('Date') == day_data.get('Date') 
                                and row.get('Team', '').lower() == team_name.lower()), None)
                
                # Get completed sections for this date and team
                all_sections = get_sheet_data(COMPLETED_SECTIONS_SHEET)
                
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
                                     date_str=date_str,
                                     team_data=team_data,
                                     team_name=team_name,
                                     kids_sections=kids_sections)
            else:
                return redirect(url_for('home'))
        except Exception as e:
            return redirect(url_for('home'))

    @app.route('/home/<date_str>/team/<team_name>/record_section')
    def record_section_form(date_str, team_name):
        try:
            # Get schedule data
            schedule_data = get_sheet_data(SCHEDULE_SHEET)
            
            # Convert URL date back to display format for matching
            display_date = url_to_date(date_str)
            day_data = find_day_by_date(schedule_data, display_date)
            
            if day_data:
                # Get team kids from Master Roster
                roster_data = get_sheet_data(MASTER_ROSTER_SHEET)
                team_kids = [row['Name'] for row in roster_data if row.get('Group', '').lower() == team_name.lower()]
                
                return render_template('record_section_form.html',
                                     day_data=day_data,
                                     date_str=date_str,
                                     team_name=team_name,
                                     team_kids=team_kids,
                                     schedule_data=schedule_data)
            else:
                return redirect(url_for('home'))
        except Exception as e:
            return redirect(url_for('home'))

    @app.route('/home/<date_str>/team/<team_name>/kid/<path:kid_name>/section/<path:section_name>')
    def home_section_details(date_str, team_name, kid_name, section_name):
        # Get section completion details
        try:
            schedule_data = get_sheet_data(SCHEDULE_SHEET)
            
            # Convert URL date back to display format for matching
            display_date = url_to_date(date_str)
            day_data = find_day_by_date(schedule_data, display_date)
            
            if day_data:
                # Get completed sections for this specific entry
                all_sections = get_sheet_data(COMPLETED_SECTIONS_SHEET)
                
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
                                     date_str=date_str,
                                     team_name=team_name,
                                     kid_name=kid_name,
                                     section_name=section_name,
                                     section_entry=section_entry)
            else:
                return redirect(url_for('home'))
        except Exception as e:
            print(f"Error in home_section_details: {e}")
            return redirect(url_for('home'))

    @app.route('/submit_section', methods=['POST'])
    def submit_section():
        try:
            # Get form data
            name = request.form.get('name')
            date = request.form.get('date')
            team = request.form.get('team')
            date_str = request.form.get('date_str')
            section = request.form.get('section')
            
            # Get completed sections sheet and headers
            completed_sections_sheet = spreadsheet.worksheet(COMPLETED_SECTIONS_SHEET)
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
            
            return redirect(f'/home/{date_str}/team/{team}')
        except Exception as e:
            return redirect(url_for('home'))

    @app.route('/edit_section', methods=['GET', 'POST'])
    def edit_section():
        # Handle GET requests (redirect back)
        if request.method == 'GET':
            return redirect(url_for('home'))
        
        # Update section completion in Google Sheets
        try:
            date_str = request.form.get('date_str')
            team_name = request.form.get('team_name')
            kid_name = request.form.get('kid_name')
            section_name = request.form.get('section_name')
            
            schedule_data = get_sheet_data(SCHEDULE_SHEET)
            
            # Convert URL date back to display format for matching
            display_date = url_to_date(date_str)
            day_data = find_day_by_date(schedule_data, display_date)
            
            if day_data:
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
                        protected_fields = ['date_str', 'team_name', 'kid_name', 'section_name', 'Name', 'Team', 'Date', 'Section', 'Timestamp', 'timestamp']
                        
                        for field_name in entry.keys():
                            if field_name not in protected_fields:
                                try:
                                    col_index = headers.index(field_name) + 1
                                    value = 'TRUE' if field_name in request.form else 'FALSE'
                                    completed_sections_sheet.update_cell(row_num, col_index, value)
                                except ValueError:
                                    continue
                        break
                
                return redirect(f'/home/{date_str}/team/{team_name}/kid/{kid_name}/section/{section_name}')
            
            return redirect(url_for('home'))
        except Exception as e:
            return redirect(url_for('home'))