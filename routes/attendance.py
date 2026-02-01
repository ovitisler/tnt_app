from flask import render_template, request, redirect, url_for
from datetime import datetime
from urllib.parse import unquote

from models.sheets import (
    get_sheet_data,
    get_worksheet,
    cache_append_row,
    cache_update_row,
    refresh_computed_sheets,
    ATTENDANCE_SCHEDULE_SHEET,
    WEEKLY_ATTENDANCE_TOTALS_SHEET,
    ATTENDANCE_ENTRIES_SHEET,
    MASTER_ROSTER_SHEET,
)
from models.utils import dates_match, find_day_by_date, url_to_date

def register_attendance_routes(app):
    """Register all attendance-related routes"""
    
    @app.route('/attendance')
    def attendance():
        # Get attendance schedule data from the sheet
        try:
            schedule_data = get_sheet_data(ATTENDANCE_SCHEDULE_SHEET)
            return render_template('attendance.html', schedule_data=schedule_data)
        except Exception as e:
            # If sheet doesn't exist or error occurs, return empty data
            return render_template('attendance.html', schedule_data=[], error=str(e))

    @app.route('/attendance/<date_str>')
    def attendance_details(date_str):
        # Get attendance schedule data and show details for specific day
        try:
            schedule_data = get_sheet_data(ATTENDANCE_SCHEDULE_SHEET)
            
            # Convert URL date back to display format for matching
            display_date = url_to_date(date_str)
            day_data = find_day_by_date(schedule_data, display_date)
            
            if day_data:
                # Get weekly attendance totals for this date
                all_totals = get_sheet_data(WEEKLY_ATTENDANCE_TOTALS_SHEET)
                
                # Filter totals by matching date
                date_totals = [row for row in all_totals if row.get('Date') == day_data.get('Date')]
                
                return render_template('attendance_details.html', 
                                     day_data=day_data, 
                                     date_str=date_str,
                                     weekly_totals=date_totals)
            else:
                return redirect(url_for('attendance'))
        except Exception as e:
            return redirect(url_for('attendance'))

    @app.route('/attendance/<date_str>/team/<team_name>')
    def team_attendance_details(date_str, team_name):
        # Get team attendance details for specific day and team
        try:
            schedule_data = get_sheet_data(ATTENDANCE_SCHEDULE_SHEET)
            
            # Convert URL date back to display format for matching
            display_date = url_to_date(date_str)
            day_data = find_day_by_date(schedule_data, display_date)
            
            if day_data:
                # Get weekly attendance totals for this date and team
                all_totals = get_sheet_data(WEEKLY_ATTENDANCE_TOTALS_SHEET)
                
                # Find the specific team data
                team_data = next((row for row in all_totals 
                                if row.get('Date') == day_data.get('Date') 
                                and row.get('Team', '').lower() == team_name.lower()), None)
                
                # Get attendance entries for this date and team
                all_entries = get_sheet_data(ATTENDANCE_ENTRIES_SHEET)
                
                # Filter entries by date and team using flexible date matching
                checked_in_kids = [entry for entry in all_entries 
                                 if dates_match(entry.get('Date'), day_data.get('Date')) 
                                 and entry.get('Team', '').lower() == team_name.lower()]
                
                return render_template('team_attendance_details.html', 
                                     day_data=day_data, 
                                     date_str=date_str,
                                     team_data=team_data,
                                     team_name=team_name,
                                     checked_in_kids=checked_in_kids)
            else:
                return redirect(url_for('attendance'))
        except Exception as e:
            return redirect(url_for('attendance'))

    @app.route('/attendance/<date_str>/team/<team_name>/kid/<path:kid_name>')
    def kid_attendance_details(date_str, team_name, kid_name):
        # Get individual kid attendance details
        try:
            schedule_data = get_sheet_data(ATTENDANCE_SCHEDULE_SHEET)
            
            # Convert URL date back to display format for matching
            display_date = url_to_date(date_str)
            day_data = find_day_by_date(schedule_data, display_date)
            
            if day_data:
                # Get attendance entries for this specific kid, date, and team
                all_entries = get_sheet_data(ATTENDANCE_ENTRIES_SHEET)
                
                # Decode URL-encoded parameters
                kid_name = unquote(kid_name)
                
                # Find the specific kid's entry
                kid_entry = next((entry for entry in all_entries 
                                if dates_match(entry.get('Date'), day_data.get('Date')) 
                                and entry.get('Team', '').lower() == team_name.lower()
                                and entry.get('Name', '').lower() == kid_name.lower()), None)
                
                return render_template('kid_attendance_details.html', 
                                     day_data=day_data, 
                                     date_str=date_str,
                                     team_name=team_name,
                                     kid_name=kid_name,
                                     kid_entry=kid_entry)
            else:
                return redirect(url_for('attendance'))
        except Exception as e:
            return redirect(url_for('attendance'))

    @app.route('/attendance/<date_str>/team/<team_name>/checkin')
    def checkin_form(date_str, team_name):
        try:
            # Get attendance schedule data
            schedule_data = get_sheet_data(ATTENDANCE_SCHEDULE_SHEET)
            
            # Convert URL date back to display format for matching
            display_date = url_to_date(date_str)
            day_data = find_day_by_date(schedule_data, display_date)
            
            if day_data:
                # Get team kids from Master Roster
                roster_data = get_sheet_data(MASTER_ROSTER_SHEET)
                team_kids = [row['Name'] for row in roster_data if row.get('Group', '').lower() == team_name.lower()]
                
                return render_template('checkin_form.html',
                                     day_data=day_data,
                                     date_str=date_str,
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
            date_str = request.form.get('date_str')
            
            # Get attendance entries sheet and headers
            attendance_entries_sheet = get_worksheet(ATTENDANCE_ENTRIES_SHEET)
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

            # Write-through: update cache with new row
            cache_append_row(ATTENDANCE_ENTRIES_SHEET, data_map)
            # Trigger background refresh for computed Totals sheet
            refresh_computed_sheets(ATTENDANCE_ENTRIES_SHEET)

            return redirect(f'/attendance/{date_str}/team/{team}')
        except Exception as e:
            return redirect(url_for('attendance'))

    @app.route('/edit_attendance', methods=['GET', 'POST'])
    def edit_kid_attendance():
        # Handle GET requests (redirect back)
        if request.method == 'GET':
            return redirect(url_for('attendance'))
        
        # Update kid attendance in Google Sheets
        try:
            date_str = request.form.get('date_str')
            team_name = request.form.get('team_name')
            kid_name = request.form.get('kid_name')
            
            schedule_data = get_sheet_data(ATTENDANCE_SCHEDULE_SHEET)
            
            # Convert URL date back to display format for matching
            display_date = url_to_date(date_str)
            day_data = find_day_by_date(schedule_data, display_date)
            
            if day_data:
                # Get attendance entries sheet
                attendance_entries_sheet = get_worksheet(ATTENDANCE_ENTRIES_SHEET)
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
                        protected_fields = ['date_str', 'team_name', 'kid_name', 'Name', 'Team', 'Date', 'Timestamp', 'timestamp']
                        updates = {}

                        for field_name in entry.keys():
                            if field_name not in protected_fields:
                                try:
                                    col_index = headers.index(field_name) + 1
                                    value = 'TRUE' if field_name in request.form else 'FALSE'
                                    attendance_entries_sheet.update_cell(row_num, col_index, value)
                                    updates[field_name] = value
                                except ValueError:
                                    continue

                        # Write-through: update cache
                        cache_update_row(
                            ATTENDANCE_ENTRIES_SHEET,
                            lambda row: (dates_match(row.get('Date'), day_data.get('Date'))
                                        and row.get('Team', '').lower() == team_name.lower()
                                        and row.get('Name', '').lower() == kid_name.lower()),
                            updates
                        )
                        # Trigger background refresh for computed Totals sheet
                        refresh_computed_sheets(ATTENDANCE_ENTRIES_SHEET)
                        break

                return redirect(f'/attendance/{date_str}/team/{team_name}/kid/{kid_name}')
            
            return redirect(url_for('attendance'))
        except Exception as e:
            return redirect(url_for('attendance'))