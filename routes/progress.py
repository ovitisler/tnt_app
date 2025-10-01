from flask import render_template, request, redirect, url_for
from urllib.parse import unquote

from models.sheets import get_spreadsheet

# Sheet name constants
MASTER_ROSTER_SHEET = 'Master Roster'
COMPLETED_SECTIONS_SHEET = 'Completed Sections RAW'

# Get spreadsheet instance
spreadsheet = get_spreadsheet()

# Helper function
def get_sheet_data(sheet_name):
    """Get data from any sheet"""
    return spreadsheet.worksheet(sheet_name).get_all_records()

def register_progress_routes(app):
    """Register all progress-related routes"""
    
    @app.route('/progress')
    def progress():
        try:
            # Get all students from Master Roster
            roster_data = get_sheet_data(MASTER_ROSTER_SHEET)
            
            return render_template('progress.html', students=roster_data)
        except Exception as e:
            return render_template('progress.html', students=[], error=str(e))

    @app.route('/progress/student/<path:student_name>')
    def student_progress(student_name):
        try:
            student_name = unquote(student_name)
            
            # Get student info from Master Roster
            roster_data = get_sheet_data(MASTER_ROSTER_SHEET)
            student_info = next((student for student in roster_data if student.get('Name', '').lower() == student_name.lower()), None)
            
            # Get all completed sections for this student
            all_sections = get_sheet_data(COMPLETED_SECTIONS_SHEET)
            
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
            all_sections = get_sheet_data(COMPLETED_SECTIONS_SHEET)
            
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
            completed_sections_sheet = spreadsheet.worksheet(COMPLETED_SECTIONS_SHEET)
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