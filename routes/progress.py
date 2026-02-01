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
            student_info = next((student for student in roster_data if student.get(NAME, '').lower() == student_name.lower()), None)

            all_sections = get_completed_sections()

            student_sections = [section for section in all_sections if section.get(NAME, '').lower() == student_name.lower()]

            total_sections = len(student_sections)
            silver_earned = sum(1 for section in student_sections if str(section.get(SILVER_CREDIT, '')).lower() in ['true', 'yes', '1'])
            gold_earned = sum(1 for section in student_sections if str(section.get(GOLD_CREDIT, '')).lower() in ['true', 'yes', '1'])

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

            all_sections = get_completed_sections()

            student_sections = [section for section in all_sections if section.get(NAME, '').lower() == student_name.lower()]

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

                return redirect(f'/progress/student/{student_name}/section/{section_index}')

            return redirect(url_for('progress'))
        except Exception as e:
            return redirect(url_for('progress'))
