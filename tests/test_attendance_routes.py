import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to Python path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from routes.attendance import register_attendance_routes

class TestAttendanceRoutes(unittest.TestCase):
    
    # Common test data
    SAMPLE_SCHEDULE_DATA = [
        {'Date': 'September 17, 2025', 'Theme': 'Test Theme'}
    ]
    
    SAMPLE_TOTALS_DATA = [
        {'Date': 'September 17, 2025', 'Team': 'Red', 'Kids Present': 5, 'Attendance Points': 25}
    ]
    
    SAMPLE_ENTRIES_DATA = [
        {'Date': 'September 17, 2025', 'Team': 'Red', 'Name': 'John Doe', 'Present': True},
        {'Date': 'September 17, 2025', 'Team': 'Red', 'Name': 'Jane Smith', 'Present': True}
    ]
    
    SAMPLE_ROSTER_DATA = [
        {'Name': 'John Doe', 'Group': 'Red'},
        {'Name': 'Jane Smith', 'Group': 'Red'},
        {'Name': 'Bob Wilson', 'Group': 'Blue'}
    ]
    
    TEST_DATE_STR = '2025-09-17'  # URL format for September 17, 2025
    
    SAMPLE_HEADERS = ['timestamp', 'Name', 'Team', 'Date', 'Present', 'Has Bible', 'Wearing Shirt?', 'Has Book?', 'Did Homework?', 'Has Dues?']
    
    def setUp(self):
        """Set up test Flask app with attendance routes"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
        # Add the date_to_url filter
        from models.utils import date_to_url
        self.app.jinja_env.filters['date_to_url'] = date_to_url
        
        register_attendance_routes(self.app)
        self.client = self.app.test_client()
    
    def create_mock_sheets(self, schedule_data=None, totals_data=None, entries_data=None, roster_data=None):
        """Helper method to create mock sheets with data"""
        mock_schedule_sheet = Mock()
        mock_schedule_sheet.get_all_records.return_value = schedule_data or self.SAMPLE_SCHEDULE_DATA
        
        mock_totals_sheet = Mock()
        mock_totals_sheet.get_all_records.return_value = totals_data or self.SAMPLE_TOTALS_DATA
        
        mock_entries_sheet = Mock()
        mock_entries_sheet.get_all_records.return_value = entries_data or self.SAMPLE_ENTRIES_DATA
        
        mock_roster_sheet = Mock()
        mock_roster_sheet.get_all_records.return_value = roster_data or self.SAMPLE_ROSTER_DATA
        
        return mock_schedule_sheet, mock_totals_sheet, mock_entries_sheet, mock_roster_sheet
    
    @patch('routes.attendance.render_template')
    @patch('routes.attendance.spreadsheet')
    def test_attendance_route_success(self, mock_spreadsheet, mock_render):
        """Test attendance route with successful data retrieval"""
        mock_schedule_sheet, _, _, _ = self.create_mock_sheets()
        mock_spreadsheet.worksheet.return_value = mock_schedule_sheet
        mock_render.return_value = 'rendered template'
        
        response = self.client.get('/attendance')
        self.assertEqual(response.status_code, 200)
        
        mock_render.assert_called_once_with(
            'attendance.html',
            schedule_data=self.SAMPLE_SCHEDULE_DATA
        )
    
    @patch('routes.attendance.render_template')
    @patch('routes.attendance.spreadsheet')
    def test_attendance_route_error(self, mock_spreadsheet, mock_render):
        """Test attendance route with sheet access error"""
        mock_spreadsheet.worksheet.side_effect = Exception("Sheet not found")
        mock_render.return_value = 'rendered template'
        
        response = self.client.get('/attendance')
        self.assertEqual(response.status_code, 200)
        
        mock_render.assert_called_once_with(
            'attendance.html',
            schedule_data=[],
            error="Sheet not found"
        )
    
    @patch('routes.attendance.render_template')
    @patch('routes.attendance.spreadsheet')
    def test_attendance_details_valid_date(self, mock_spreadsheet, mock_render):
        """Test attendance_details with valid date"""
        mock_schedule_sheet, mock_totals_sheet, _, _ = self.create_mock_sheets()
        
        mock_spreadsheet.worksheet.side_effect = lambda name: {
            'Attendance Schedule': mock_schedule_sheet,
            'Weekly Attendance Totals': mock_totals_sheet
        }[name]
        
        mock_render.return_value = 'rendered template'
        
        response = self.client.get(f'/attendance/{self.TEST_DATE_STR}')
        self.assertEqual(response.status_code, 200)
        
        mock_render.assert_called_once_with(
            'attendance_details.html',
            day_data=self.SAMPLE_SCHEDULE_DATA[0],
            date_str=self.TEST_DATE_STR,
            weekly_totals=self.SAMPLE_TOTALS_DATA
        )
    
    @patch('routes.attendance.spreadsheet')
    def test_attendance_details_invalid_date(self, mock_spreadsheet):
        """Test attendance_details with invalid date (should redirect)"""
        mock_schedule_sheet, _, _, _ = self.create_mock_sheets()
        mock_spreadsheet.worksheet.return_value = mock_schedule_sheet
        
        response = self.client.get('/attendance/2025-12-25')
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertIn('/attendance', response.location)
    
    @patch('routes.attendance.render_template')
    @patch('routes.attendance.spreadsheet')
    def test_team_attendance_details_success(self, mock_spreadsheet, mock_render):
        """Test team_attendance_details with valid parameters"""
        mock_schedule_sheet, mock_totals_sheet, mock_entries_sheet, _ = self.create_mock_sheets()
        
        mock_spreadsheet.worksheet.side_effect = lambda name: {
            'Attendance Schedule': mock_schedule_sheet,
            'Weekly Attendance Totals': mock_totals_sheet,
            'Attendance Entries RAW': mock_entries_sheet
        }[name]
        
        mock_render.return_value = 'rendered template'
        
        response = self.client.get(f'/attendance/{self.TEST_DATE_STR}/team/Red')
        self.assertEqual(response.status_code, 200)
        
        mock_render.assert_called_once()
        call_args = mock_render.call_args[1]
        self.assertEqual(call_args['team_name'], 'Red')
        self.assertEqual(call_args['date_str'], self.TEST_DATE_STR)
        self.assertEqual(len(call_args['checked_in_kids']), 2)  # John Doe and Jane Smith
    
    @patch('routes.attendance.spreadsheet')
    def test_team_attendance_details_invalid_date(self, mock_spreadsheet):
        """Test team_attendance_details with invalid date"""
        mock_schedule_sheet, _, _, _ = self.create_mock_sheets()
        mock_spreadsheet.worksheet.return_value = mock_schedule_sheet
        
        response = self.client.get('/attendance/2025-12-25/team/Red')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/attendance', response.location)
    
    @patch('routes.attendance.render_template')
    @patch('routes.attendance.spreadsheet')
    def test_kid_attendance_details_success(self, mock_spreadsheet, mock_render):
        """Test kid_attendance_details with valid parameters"""
        mock_schedule_sheet, _, mock_entries_sheet, _ = self.create_mock_sheets()
        
        mock_spreadsheet.worksheet.side_effect = lambda name: {
            'Attendance Schedule': mock_schedule_sheet,
            'Attendance Entries RAW': mock_entries_sheet
        }[name]
        
        mock_render.return_value = 'rendered template'
        
        response = self.client.get(f'/attendance/{self.TEST_DATE_STR}/team/Red/kid/John%20Doe')
        self.assertEqual(response.status_code, 200)
        
        mock_render.assert_called_once()
        call_args = mock_render.call_args[1]
        self.assertEqual(call_args['kid_name'], 'John Doe')
        self.assertEqual(call_args['team_name'], 'Red')
        self.assertIsNotNone(call_args['kid_entry'])
    
    @patch('routes.attendance.render_template')
    @patch('routes.attendance.spreadsheet')
    def test_checkin_form_success(self, mock_spreadsheet, mock_render):
        """Test checkin_form with valid parameters"""
        mock_schedule_sheet, _, _, mock_roster_sheet = self.create_mock_sheets()
        
        mock_spreadsheet.worksheet.side_effect = lambda name: {
            'Attendance Schedule': mock_schedule_sheet,
            'Master Roster': mock_roster_sheet
        }[name]
        
        mock_render.return_value = 'rendered template'
        
        response = self.client.get(f'/attendance/{self.TEST_DATE_STR}/team/Red/checkin')
        self.assertEqual(response.status_code, 200)
        
        mock_render.assert_called_once()
        call_args = mock_render.call_args[1]
        self.assertEqual(call_args['team_name'], 'Red')
        self.assertEqual(call_args['team_kids'], ['John Doe', 'Jane Smith'])  # Only Red team members
    
    @patch('routes.attendance.spreadsheet')
    def test_submit_checkin_success(self, mock_spreadsheet):
        """Test submit_checkin with valid form data"""
        mock_entries_sheet = Mock()
        mock_entries_sheet.row_values.return_value = self.SAMPLE_HEADERS
        mock_entries_sheet.append_row = Mock()
        
        mock_spreadsheet.worksheet.return_value = mock_entries_sheet
        
        form_data = {
            'name': 'John Doe',
            'date': 'September 17, 2025',
            'team': 'Red',
            'date_str': self.TEST_DATE_STR,
            'present': 'on',
            'has_bible': 'on'
        }
        
        response = self.client.post('/submit_checkin', data=form_data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertIn(f'/attendance/{self.TEST_DATE_STR}/team/Red', response.location)
        
        # Verify append_row was called
        mock_entries_sheet.append_row.assert_called_once()
    
    @patch('routes.attendance.spreadsheet')
    def test_submit_checkin_error(self, mock_spreadsheet):
        """Test submit_checkin with sheet error"""
        mock_spreadsheet.worksheet.side_effect = Exception("Sheet error")
        
        form_data = {
            'name': 'John Doe',
            'date': 'September 17, 2025',
            'team': 'Red',
            'date_str': self.TEST_DATE_STR
        }
        
        response = self.client.post('/submit_checkin', data=form_data)
        self.assertEqual(response.status_code, 302)  # Redirect to attendance on error
        self.assertIn('/attendance', response.location)
    
    @patch('routes.attendance.spreadsheet')
    def test_edit_kid_attendance_get_redirect(self, mock_spreadsheet):
        """Test edit_kid_attendance GET request redirects to attendance"""
        response = self.client.get('/edit_attendance')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/attendance', response.location)
    
    @patch('routes.attendance.spreadsheet')
    def test_edit_kid_attendance_post_success(self, mock_spreadsheet):
        """Test edit_kid_attendance POST with successful update"""
        mock_schedule_sheet = Mock()
        mock_schedule_sheet.get_all_records.return_value = self.SAMPLE_SCHEDULE_DATA
        
        mock_entries_sheet = Mock()
        mock_entries_sheet.get_all_records.return_value = self.SAMPLE_ENTRIES_DATA
        mock_entries_sheet.row_values.return_value = self.SAMPLE_HEADERS
        mock_entries_sheet.update_cell = Mock()
        
        mock_spreadsheet.worksheet.side_effect = lambda name: {
            'Attendance Schedule': mock_schedule_sheet,
            'Attendance Entries RAW': mock_entries_sheet
        }[name]
        
        form_data = {
            'date_str': self.TEST_DATE_STR,
            'team_name': 'Red',
            'kid_name': 'John Doe',
            'Present': 'on',
            'Has Bible': 'on'
        }
        
        response = self.client.post('/edit_attendance', data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'/attendance/{self.TEST_DATE_STR}/team/Red/kid/John%20Doe', response.location)
        
        # Verify update_cell was called
        mock_entries_sheet.update_cell.assert_called()
    
    @patch('routes.attendance.spreadsheet')
    def test_edit_kid_attendance_post_invalid_date(self, mock_spreadsheet):
        """Test edit_kid_attendance POST with invalid date"""
        mock_schedule_sheet = Mock()
        mock_schedule_sheet.get_all_records.return_value = self.SAMPLE_SCHEDULE_DATA
        mock_spreadsheet.worksheet.return_value = mock_schedule_sheet
        
        form_data = {
            'date_str': '2025-12-25',  # Invalid date not in schedule
            'team_name': 'Red',
            'kid_name': 'John Doe'
        }
        
        response = self.client.post('/edit_attendance', data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/attendance', response.location)
    
    @patch('routes.attendance.spreadsheet')
    def test_edit_kid_attendance_post_no_match(self, mock_spreadsheet):
        """Test edit_kid_attendance POST when no matching entry is found"""
        mock_schedule_sheet = Mock()
        mock_schedule_sheet.get_all_records.return_value = self.SAMPLE_SCHEDULE_DATA
        
        mock_entries_sheet = Mock()
        mock_entries_sheet.get_all_records.return_value = []  # No matching entries
        
        mock_spreadsheet.worksheet.side_effect = lambda name: {
            'Attendance Schedule': mock_schedule_sheet,
            'Attendance Entries RAW': mock_entries_sheet
        }[name]
        
        form_data = {
            'date_str': self.TEST_DATE_STR,
            'team_name': 'Red',
            'kid_name': 'John Doe'
        }
        
        response = self.client.post('/edit_attendance', data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'/attendance/{self.TEST_DATE_STR}/team/Red/kid/John%20Doe', response.location)
    
    @patch('routes.attendance.spreadsheet')
    def test_edit_kid_attendance_post_error(self, mock_spreadsheet):
        """Test edit_kid_attendance POST with sheet error"""
        mock_spreadsheet.worksheet.side_effect = Exception("Sheet error")
        
        form_data = {
            'date_str': self.TEST_DATE_STR,
            'team_name': 'Red',
            'kid_name': 'John Doe'
        }
        
        response = self.client.post('/edit_attendance', data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/attendance', response.location)


if __name__ == '__main__':
    unittest.main()