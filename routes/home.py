from collections import defaultdict
from urllib.parse import unquote

from flask import render_template, request, redirect, url_for

from models.fields import (
    NAME, TEAM, DATE, GROUP, SECTION,
    SECTION_COMPLETE, SILVER_CREDIT, GOLD_CREDIT,
)
from models.data import (
    get_schedule,
    get_roster,
    get_weekly_totals,
    get_completed_sections,
    insert_completed_section,
    update_completed_section,
)
from models.utils import dates_match, find_day_by_date, url_to_date


def register_home_routes(app):
    """Register all home-related routes"""

    @app.route('/')
    def home():
        try:
            schedule_data = get_schedule()
            return render_template('home.html', schedule_data=schedule_data)
        except Exception as e:
            return render_template('home.html', schedule_data=[], error=str(e))

    @app.route('/home/<date_str>')
    def home_details(date_str):
        try:
            schedule_data = get_schedule()

            display_date = url_to_date(date_str)
            day_data = find_day_by_date(schedule_data, display_date)

            if day_data:
                all_totals = get_weekly_totals()
                date_totals = [row for row in all_totals if row.get(DATE) == day_data.get(DATE)]

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
        try:
            schedule_data = get_schedule()

            display_date = url_to_date(date_str)
            day_data = find_day_by_date(schedule_data, display_date)

            if day_data:
                all_totals = get_weekly_totals()

                team_data = next((row for row in all_totals
                                if row.get(DATE) == day_data.get(DATE)
                                and row.get(TEAM, '').lower() == team_name.lower()), None)

                all_sections = get_completed_sections()

                team_sections = [entry for entry in all_sections
                               if dates_match(entry.get(DATE), day_data.get(DATE))
                               and entry.get(TEAM, '').lower() == team_name.lower()]

                kids_sections = defaultdict(list)
                for section in team_sections:
                    kid_name = section.get(NAME, '')
                    if kid_name:
                        kids_sections[kid_name].append(section.get(SECTION, ''))

                return render_template('home_team_details.html',
                                     day_data=day_data,
                                     date_str=date_str,
                                     team_data=team_data,
                                     team_name=team_name,
                                     kids_sections=dict(kids_sections))
            else:
                return redirect(url_for('home'))
        except Exception as e:
            return redirect(url_for('home'))

    @app.route('/home/<date_str>/team/<team_name>/record_section')
    def record_section_form(date_str, team_name):
        try:
            schedule_data = get_schedule()

            display_date = url_to_date(date_str)
            day_data = find_day_by_date(schedule_data, display_date)

            if day_data:
                roster_data = get_roster()
                team_kids = [row[NAME] for row in roster_data if row.get(GROUP, '').lower() == team_name.lower()]

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
        try:
            schedule_data = get_schedule()

            display_date = url_to_date(date_str)
            day_data = find_day_by_date(schedule_data, display_date)

            if day_data:
                all_sections = get_completed_sections()

                kid_name = unquote(kid_name)
                section_name = unquote(section_name)

                section_entry = next((entry for entry in all_sections
                                    if dates_match(entry.get(DATE), day_data.get(DATE))
                                    and entry.get(TEAM, '').lower() == team_name.lower()
                                    and entry.get(NAME, '').lower() == kid_name.lower()
                                    and str(entry.get(SECTION, '')) == str(section_name)), None)

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
            date_str = request.form.get('date_str')
            team = request.form.get('team')

            insert_completed_section({
                NAME: request.form.get('name'),
                TEAM: team,
                DATE: request.form.get('date'),
                SECTION: request.form.get('section'),
                SECTION_COMPLETE: SECTION_COMPLETE in request.form,
                SILVER_CREDIT: SILVER_CREDIT in request.form,
                GOLD_CREDIT: GOLD_CREDIT in request.form,
            })

            return redirect(f'/home/{date_str}/team/{team}')
        except Exception as e:
            return redirect(url_for('home'))

    @app.route('/edit_section', methods=['GET', 'POST'])
    def edit_section():
        if request.method == 'GET':
            return redirect(url_for('home'))

        try:
            date_str = request.form.get('date_str')
            team_name = request.form.get('team_name')
            kid_name = request.form.get('kid_name')
            section_name = request.form.get('section_name')

            schedule_data = get_schedule()
            display_date = url_to_date(date_str)
            day_data = find_day_by_date(schedule_data, display_date)

            if day_data:
                entry_date = day_data.get(DATE)

                update_completed_section(
                    lambda row: (dates_match(row.get(DATE), entry_date)
                                and row.get(TEAM, '').lower() == team_name.lower()
                                and row.get(NAME, '').lower() == kid_name.lower()
                                and str(row.get(SECTION, '')) == str(section_name)),
                    {
                        SECTION_COMPLETE: 'TRUE' if SECTION_COMPLETE in request.form else 'FALSE',
                        SILVER_CREDIT: 'TRUE' if SILVER_CREDIT in request.form else 'FALSE',
                        GOLD_CREDIT: 'TRUE' if GOLD_CREDIT in request.form else 'FALSE',
                    }
                )

                return redirect(f'/home/{date_str}/team/{team_name}/kid/{kid_name}/section/{section_name}')

            return redirect(url_for('home'))
        except Exception as e:
            return redirect(url_for('home'))
