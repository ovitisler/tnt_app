from flask import render_template, request, redirect, url_for
from urllib.parse import unquote

from models.data import get_records, insert_record, update_record
from models.sheets import (
    ATTENDANCE_SCHEDULE_SHEET,
    WEEKLY_ATTENDANCE_TOTALS_SHEET,
    ATTENDANCE_ENTRIES_SHEET,
    MASTER_ROSTER_SHEET,
)
from models.fields import (
    NAME, TEAM, DATE, GROUP,
    PRESENT, HAS_BIBLE, WEARING_SHIRT, HAS_BOOK, DID_HOMEWORK, HAS_DUES,
)
from models.utils import dates_match, find_day_by_date, url_to_date

def register_attendance_routes(app):
    """Register all attendance-related routes"""
    
    @app.route('/attendance')
    def attendance():
        # Get attendance schedule data from the sheet
        try:
            schedule_data = get_records(ATTENDANCE_SCHEDULE_SHEET)
            return render_template('attendance.html', schedule_data=schedule_data)
        except Exception as e:
            # If sheet doesn't exist or error occurs, return empty data
            return render_template('attendance.html', schedule_data=[], error=str(e))

    @app.route('/attendance/<date_str>')
    def attendance_details(date_str):
        # Get attendance schedule data and show details for specific day
        try:
            schedule_data = get_records(ATTENDANCE_SCHEDULE_SHEET)
            
            # Convert URL date back to display format for matching
            display_date = url_to_date(date_str)
            day_data = find_day_by_date(schedule_data, display_date)
            
            if day_data:
                # Get weekly attendance totals for this date
                all_totals = get_records(WEEKLY_ATTENDANCE_TOTALS_SHEET)
                
                # Filter totals by matching date
                date_totals = [row for row in all_totals if row.get(DATE) == day_data.get(DATE)]
                
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
            schedule_data = get_records(ATTENDANCE_SCHEDULE_SHEET)
            
            # Convert URL date back to display format for matching
            display_date = url_to_date(date_str)
            day_data = find_day_by_date(schedule_data, display_date)
            
            if day_data:
                # Get weekly attendance totals for this date and team
                all_totals = get_records(WEEKLY_ATTENDANCE_TOTALS_SHEET)
                
                # Find the specific team data
                team_data = next((row for row in all_totals
                                if row.get(DATE) == day_data.get(DATE)
                                and row.get(TEAM, '').lower() == team_name.lower()), None)
                
                # Get attendance entries for this date and team
                all_entries = get_records(ATTENDANCE_ENTRIES_SHEET)
                
                # Filter entries by date and team using flexible date matching
                checked_in_kids = [entry for entry in all_entries
                                 if dates_match(entry.get(DATE), day_data.get(DATE))
                                 and entry.get(TEAM, '').lower() == team_name.lower()]
                
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
            schedule_data = get_records(ATTENDANCE_SCHEDULE_SHEET)
            
            # Convert URL date back to display format for matching
            display_date = url_to_date(date_str)
            day_data = find_day_by_date(schedule_data, display_date)
            
            if day_data:
                # Get attendance entries for this specific kid, date, and team
                all_entries = get_records(ATTENDANCE_ENTRIES_SHEET)
                
                # Decode URL-encoded parameters
                kid_name = unquote(kid_name)
                
                # Find the specific kid's entry
                kid_entry = next((entry for entry in all_entries
                                if dates_match(entry.get(DATE), day_data.get(DATE))
                                and entry.get(TEAM, '').lower() == team_name.lower()
                                and entry.get(NAME, '').lower() == kid_name.lower()), None)
                
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
            schedule_data = get_records(ATTENDANCE_SCHEDULE_SHEET)
            
            # Convert URL date back to display format for matching
            display_date = url_to_date(date_str)
            day_data = find_day_by_date(schedule_data, display_date)
            
            if day_data:
                # Get team kids from Master Roster
                roster_data = get_records(MASTER_ROSTER_SHEET)
                team_kids = [row[NAME] for row in roster_data if row.get(GROUP, '').lower() == team_name.lower()]
                
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
            date_str = request.form.get('date_str')
            team = request.form.get('team')

            insert_record(ATTENDANCE_ENTRIES_SHEET, {
                NAME: request.form.get('name'),
                TEAM: team,
                DATE: request.form.get('date'),
                PRESENT: 'present' in request.form,
                HAS_BIBLE: 'has_bible' in request.form,
                WEARING_SHIRT: 'wearing_shirt' in request.form,
                HAS_BOOK: 'has_book' in request.form,
                DID_HOMEWORK: 'did_homework' in request.form,
                HAS_DUES: 'has_dues' in request.form,
            })

            return redirect(f'/attendance/{date_str}/team/{team}')
        except Exception as e:
            return redirect(url_for('attendance'))

    @app.route('/edit_attendance', methods=['GET', 'POST'])
    def edit_kid_attendance():
        if request.method == 'GET':
            return redirect(url_for('attendance'))

        try:
            date_str = request.form.get('date_str')
            team_name = request.form.get('team_name')
            kid_name = request.form.get('kid_name')

            schedule_data = get_records(ATTENDANCE_SCHEDULE_SHEET)
            display_date = url_to_date(date_str)
            day_data = find_day_by_date(schedule_data, display_date)

            if day_data:
                entry_date = day_data.get(DATE)

                update_record(
                    ATTENDANCE_ENTRIES_SHEET,
                    lambda row: (dates_match(row.get(DATE), entry_date)
                                and row.get(TEAM, '').lower() == team_name.lower()
                                and row.get(NAME, '').lower() == kid_name.lower()),
                    {
                        PRESENT: 'TRUE' if PRESENT in request.form else 'FALSE',
                        HAS_BIBLE: 'TRUE' if HAS_BIBLE in request.form else 'FALSE',
                        WEARING_SHIRT: 'TRUE' if WEARING_SHIRT in request.form else 'FALSE',
                        HAS_BOOK: 'TRUE' if HAS_BOOK in request.form else 'FALSE',
                        DID_HOMEWORK: 'TRUE' if DID_HOMEWORK in request.form else 'FALSE',
                        HAS_DUES: 'TRUE' if HAS_DUES in request.form else 'FALSE',
                    }
                )

                return redirect(f'/attendance/{date_str}/team/{team_name}/kid/{kid_name}')

            return redirect(url_for('attendance'))
        except Exception as e:
            return redirect(url_for('attendance'))