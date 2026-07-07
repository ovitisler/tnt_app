from flask import render_template, request, redirect, url_for
from urllib.parse import unquote

from models.data import (
    get_roster,
    get_completed_sections,
    update_completed_section,
)
from models.fields import NAME, DATE, SECTION, SECTION_COMPLETE, SILVER_CREDIT, GOLD_CREDIT


def register_progress_routes(app):
    """Register all progress-related routes"""

    @app.route('/progress')
    def progress():
        try:
            roster_data = get_roster()
            return render_template('progress.html', students=roster_data)
        except Exception as e:
            return render_template('progress.html', students=[], error=str(e))

    @app.route('/progress/student/<path:student_name>')
    def student_progress(student_name):
        try:
            student_name = unquote(student_name)

            roster_data = get_roster()
            student_info = next((s for s in roster_data if s.get(NAME, '').lower() == student_name.lower()), None)

            all_sections = get_completed_sections()
            student_sections = [s for s in all_sections if s.get(NAME, '').lower() == student_name.lower()]

            coalesced = {}
            for record in student_sections:
                sec = str(record.get(SECTION, ''))
                if sec not in coalesced:
                    coalesced[sec] = {'section': sec, 'main_date': None, 'silver_date': None, 'gold_date': None}
                if str(record.get(SECTION_COMPLETE, '')).lower() in ['true', 'yes', '1']:
                    if not coalesced[sec]['main_date']:
                        coalesced[sec]['main_date'] = record.get(DATE, '')
                if str(record.get(SILVER_CREDIT, '')).lower() in ['true', 'yes', '1']:
                    if not coalesced[sec]['silver_date']:
                        coalesced[sec]['silver_date'] = record.get(DATE, '')
                if str(record.get(GOLD_CREDIT, '')).lower() in ['true', 'yes', '1']:
                    if not coalesced[sec]['gold_date']:
                        coalesced[sec]['gold_date'] = record.get(DATE, '')

            silver_earned = sum(1 for s in coalesced.values() if s['silver_date'])
            gold_earned = sum(1 for s in coalesced.values() if s['gold_date'])

            def section_sort_key(item):
                try:
                    return (1, float(item['section']))
                except ValueError:
                    return (0, item['section'])

            sorted_sections = sorted(coalesced.values(), key=section_sort_key)

            return render_template('student_progress.html',
                                 student_name=student_name,
                                 student_info=student_info,
                                 coalesced_sections=sorted_sections,
                                 total_sections=len(coalesced),
                                 silver_earned=silver_earned,
                                 gold_earned=gold_earned)
        except Exception as e:
            return redirect(url_for('progress'))

    @app.route('/progress/student/<path:student_name>/section/<path:section_name>')
    def student_section_log(student_name, section_name):
        try:
            student_name = unquote(student_name)
            section_name = unquote(section_name)

            all_sections = get_completed_sections()
            student_sections = [s for s in all_sections if s.get(NAME, '').lower() == student_name.lower()]

            section_records = [
                (i, r) for i, r in enumerate(student_sections)
                if str(r.get(SECTION, '')) == str(section_name)
            ]

            return render_template('student_section_log.html',
                                 student_name=student_name,
                                 section_name=section_name,
                                 section_records=section_records)
        except Exception as e:
            return redirect(url_for('student_progress', student_name=student_name))

    @app.route('/progress/student/<path:student_name>/record/<int:section_index>')
    def student_section_details(student_name, section_index):
        try:
            student_name = unquote(student_name)

            all_sections = get_completed_sections()
            student_sections = [s for s in all_sections if s.get(NAME, '').lower() == student_name.lower()]

            if 0 <= section_index < len(student_sections):
                section_entry = student_sections[section_index]
                return render_template('student_section_details.html',
                                     student_name=student_name,
                                     section_entry=section_entry,
                                     section_index=section_index)
            else:
                return redirect(url_for('student_progress', student_name=student_name))
        except Exception as e:
            return redirect(url_for('progress'))

    @app.route('/edit_progress_section', methods=['GET', 'POST'])
    def edit_progress_section():
        if request.method == 'GET':
            return redirect(url_for('progress'))

        try:
            student_name = request.form.get('student_name')
            section_index = int(request.form.get('section_index'))

            all_sections = get_completed_sections()
            student_sections = [s for s in all_sections if s.get(NAME, '').lower() == student_name.lower()]

            if 0 <= section_index < len(student_sections):
                target = student_sections[section_index]
                target_date = target.get(DATE)
                target_section_val = str(target.get(SECTION, ''))

                update_completed_section(
                    lambda row: (row.get(NAME, '').lower() == student_name.lower()
                                and row.get(DATE) == target_date
                                and str(row.get(SECTION, '')) == target_section_val),
                    {
                        SECTION_COMPLETE: 'TRUE' if SECTION_COMPLETE in request.form else 'FALSE',
                        SILVER_CREDIT: 'TRUE' if SILVER_CREDIT in request.form else 'FALSE',
                        GOLD_CREDIT: 'TRUE' if GOLD_CREDIT in request.form else 'FALSE',
                    }
                )

                return redirect(f'/progress/student/{student_name}/record/{section_index}')

            return redirect(url_for('progress'))
        except Exception as e:
            return redirect(url_for('progress'))
