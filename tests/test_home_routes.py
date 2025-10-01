import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to Python path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from routes.home import register_home_routes

class TestHomeRoutes(unittest.TestCase):
    
    # Common test data
    SAMPLE_SCHEDULE_DATA = [
        {'Date': 'September 17, 2025', 'Theme': 'Test Theme'}
    ]
    
    SAMPLE_TOTALS_DATA = [
        {'Date': 'September 17, 2025', 'Team': 'Red', 'Points': 100}
    ]
    
    TEST_DATE_STR = '2025-09-17'  # URL format for September 17, 2025
    
    MULTI_DATE_TOTALS_DATA = [
        {'Date': 'September 17, 2025', 'Team': 'Red', 'Points': 100},
        {'Date': 'September 18, 2025', 'Team': 'Blue', 'Points': 200},
        {'Date': 'September 17, 2025', 'Team': 'Green', 'Points': 150}
    ]
    
    SAMPLE_ROSTER_DATA = [
        {'Name': 'John Doe', 'Group': 'Red'},
        {'Name': 'Jane Smith', 'Group': 'Blue'},
        {'Name': 'Bob Wilson', 'Group': 'Red'}
    ]
    
    SAMPLE_HEADERS = ['timestamp', 'Name', 'Team', 'Date', 'Section', 'Section Complete', 'Silver Credit', 'Gold Credit']
    
    def setUp(self):
        """Set up test Flask app with home routes"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
        # Add the date_to_url filter
        from models.utils import date_to_url
        self.app.jinja_env.filters['date_to_url'] = date_to_url
        
        register_home_routes(self.app)
        self.client = self.app.test_client()
    
    def create_mock_sheets(self, schedule_data=None, totals_data=None):
        """Helper method to create mock sheets with data"""
        mock_schedule_sheet = Mock()
        mock_schedule_sheet.get_all_records.return_value = schedule_data or self.SAMPLE_SCHEDULE_DATA
        
        mock_totals_sheet = Mock()
        mock_totals_sheet.get_all_records.return_value = totals_data or self.SAMPLE_TOTALS_DATA
        
        return mock_schedule_sheet, mock_totals_sheet
    
    @patch('routes.home.render_template')
    @patch('routes.home.spreadsheet')
    def test_home_details_valid_date(self, mock_spreadsheet, mock_render):
        """Test home_details with valid date"""
        mock_schedule_sheet, mock_totals_sheet = self.create_mock_sheets()
        
        # Configure mock spreadsheet
        mock_spreadsheet.worksheet.side_effect = lambda name: {
            'Schedule': mock_schedule_sheet,
            'Weekly Totals': mock_totals_sheet
        }[name]
        
        mock_render.return_value = 'rendered template'
        
        # Test the route with date-based URL
        response = self.client.get(f'/home/{self.TEST_DATE_STR}')
        self.assertEqual(response.status_code, 200)
        
        # Verify worksheet calls
        mock_spreadsheet.worksheet.assert_any_call('Schedule')
        mock_spreadsheet.worksheet.assert_any_call('Weekly Totals')
        
        # Verify render_template was called with correct parameters
        mock_render.assert_called_once_with(
            'home_details.html',
            day_data=self.SAMPLE_SCHEDULE_DATA[0],
            date_str=self.TEST_DATE_STR,
            weekly_totals=self.SAMPLE_TOTALS_DATA
        )
    
    @patch('routes.home.spreadsheet')
    def test_home_details_invalid_date(self, mock_spreadsheet):
        """Test home_details with invalid date (should redirect)"""
        mock_schedule_sheet, _ = self.create_mock_sheets()
        mock_spreadsheet.worksheet.return_value = mock_schedule_sheet
        
        # Test with date not in schedule
        response = self.client.get('/home/2025-12-25')
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertIn('/', response.location)  # Redirects to home
    
    @patch('routes.home.spreadsheet')
    def test_home_details_malformed_date(self, mock_spreadsheet):
        """Test home_details with malformed date"""
        mock_schedule_sheet, _ = self.create_mock_sheets()
        mock_spreadsheet.worksheet.return_value = mock_schedule_sheet
        
        # Test with malformed date
        response = self.client.get('/home/invalid-date')
        self.assertEqual(response.status_code, 302)  # Should redirect on error
    
    @patch('routes.home.spreadsheet')
    def test_home_details_sheet_error(self, mock_spreadsheet):
        """Test home_details when sheet access fails"""
        # Mock an exception when accessing worksheet
        mock_spreadsheet.worksheet.side_effect = Exception("Sheet not found")
        
        # Test the route
        response = self.client.get('/home/0')
        self.assertEqual(response.status_code, 302)  # Should redirect on error
    
    @patch('routes.home.spreadsheet')
    def test_home_details_empty_schedule(self, mock_spreadsheet):
        """Test home_details with empty schedule data"""
        mock_schedule_sheet, _ = self.create_mock_sheets(schedule_data=[])
        mock_spreadsheet.worksheet.return_value = mock_schedule_sheet
        
        # Test with any index when schedule is empty
        response = self.client.get('/home/0')
        self.assertEqual(response.status_code, 302)  # Should redirect
    
    @patch('routes.home.render_template')
    @patch('routes.home.spreadsheet')
    def test_home_details_date_filtering(self, mock_spreadsheet, mock_render):
        """Test that home_details correctly filters totals by date"""
        mock_schedule_sheet, mock_totals_sheet = self.create_mock_sheets(
            totals_data=self.MULTI_DATE_TOTALS_DATA
        )
        
        mock_spreadsheet.worksheet.side_effect = lambda name: {
            'Schedule': mock_schedule_sheet,
            'Weekly Totals': mock_totals_sheet
        }[name]
        
        mock_render.return_value = 'rendered template'
        
        # Test the route with date-based URL
        response = self.client.get(f'/home/{self.TEST_DATE_STR}')
        self.assertEqual(response.status_code, 200)
        
        # Verify that only September 17, 2025 entries were passed to template
        expected_filtered_totals = [
            {'Date': 'September 17, 2025', 'Team': 'Red', 'Points': 100},
            {'Date': 'September 17, 2025', 'Team': 'Green', 'Points': 150}
        ]
        
        mock_render.assert_called_once_with(
            'home_details.html',
            day_data=self.SAMPLE_SCHEDULE_DATA[0],
            date_str=self.TEST_DATE_STR,
            weekly_totals=expected_filtered_totals
        )
    
    @patch('routes.home.render_template')
    @patch('routes.home.spreadsheet')
    def test_home_route_success(self, mock_spreadsheet, mock_render):
        """Test home route with successful data retrieval"""
        mock_schedule_sheet, _ = self.create_mock_sheets()
        mock_spreadsheet.worksheet.return_value = mock_schedule_sheet
        mock_render.return_value = 'rendered template'
        
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        mock_render.assert_called_once_with(
            'home.html',
            schedule_data=self.SAMPLE_SCHEDULE_DATA
        )
    
    @patch('routes.home.render_template')
    @patch('routes.home.spreadsheet')
    def test_home_route_error(self, mock_spreadsheet, mock_render):
        """Test home route with sheet access error"""
        mock_spreadsheet.worksheet.side_effect = Exception("Sheet not found")
        mock_render.return_value = 'rendered template'
        
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        mock_render.assert_called_once_with(
            'home.html',
            schedule_data=[],
            error="Sheet not found"
        )
    
    @patch('routes.home.render_template')
    @patch('routes.home.spreadsheet')
    def test_record_section_form_valid_date(self, mock_spreadsheet, mock_render):
        """Test record_section_form with valid parameters"""
        mock_schedule_sheet, _ = self.create_mock_sheets()
        mock_roster_sheet = Mock()
        mock_roster_sheet.get_all_records.return_value = self.SAMPLE_ROSTER_DATA
        
        mock_spreadsheet.worksheet.side_effect = lambda name: {
            'Schedule': mock_schedule_sheet,
            'Master Roster': mock_roster_sheet
        }[name]
        
        mock_render.return_value = 'rendered template'
        
        response = self.client.get(f'/home/{self.TEST_DATE_STR}/team/Red/record_section')
        self.assertEqual(response.status_code, 200)
        
        # Verify correct team kids were filtered
        expected_team_kids = ['John Doe', 'Bob Wilson']  # Only Red team members
        
        mock_render.assert_called_once_with(
            'record_section_form.html',
            day_data=self.SAMPLE_SCHEDULE_DATA[0],
            date_str=self.TEST_DATE_STR,
            team_name='Red',
            team_kids=expected_team_kids,
            schedule_data=self.SAMPLE_SCHEDULE_DATA
        )
    
    @patch('routes.home.spreadsheet')
    def test_record_section_form_invalid_date(self, mock_spreadsheet):
        """Test record_section_form with invalid date"""
        mock_schedule_sheet, _ = self.create_mock_sheets()
        mock_spreadsheet.worksheet.return_value = mock_schedule_sheet
        
        response = self.client.get('/home/2025-12-25/team/Red/record_section')
        self.assertEqual(response.status_code, 302)  # Should redirect
    
    @patch('routes.home.render_template')
    @patch('routes.home.spreadsheet')
    def test_home_team_details_success(self, mock_spreadsheet, mock_render):
        """Test home_team_details with valid parameters"""
        mock_schedule_sheet, mock_totals_sheet = self.create_mock_sheets()
        mock_sections_sheet = Mock()
        mock_sections_sheet.get_all_records.return_value = [
            {'Date': 'September 17, 2025', 'Team': 'Red', 'Name': 'John Doe', 'Section': '1.1'},
            {'Date': 'September 17, 2025', 'Team': 'Red', 'Name': 'John Doe', 'Section': '1.2'}
        ]
        
        mock_spreadsheet.worksheet.side_effect = lambda name: {
            'Schedule': mock_schedule_sheet,
            'Weekly Totals': mock_totals_sheet,
            'Completed Sections RAW': mock_sections_sheet
        }[name]
        
        mock_render.return_value = 'rendered template'
        
        response = self.client.get(f'/home/{self.TEST_DATE_STR}/team/Red')
        self.assertEqual(response.status_code, 200)
        
        # Verify kids_sections grouping
        expected_kids_sections = {'John Doe': ['1.1', '1.2']}
        
        mock_render.assert_called_once()
        call_args = mock_render.call_args[1]
        self.assertEqual(call_args['team_name'], 'Red')
        self.assertEqual(dict(call_args['kids_sections']), expected_kids_sections)
    
    @patch('routes.home.spreadsheet')
    def test_home_team_details_invalid_date(self, mock_spreadsheet):
        """Test home_team_details with invalid date"""
        mock_schedule_sheet, _ = self.create_mock_sheets()
        mock_spreadsheet.worksheet.return_value = mock_schedule_sheet
        
        response = self.client.get('/home/2025-12-25/team/Red')
        self.assertEqual(response.status_code, 302)
    
    @patch('routes.home.render_template')
    @patch('routes.home.spreadsheet')
    def test_home_section_details_success(self, mock_spreadsheet, mock_render):
        """Test home_section_details with valid parameters"""
        mock_schedule_sheet, _ = self.create_mock_sheets()
        mock_sections_sheet = Mock()
        mock_sections_sheet.get_all_records.return_value = [
            {'Date': 'September 17, 2025', 'Team': 'Red', 'Name': 'John Doe', 'Section': '1.1', 'Complete': True}
        ]
        
        mock_spreadsheet.worksheet.side_effect = lambda name: {
            'Schedule': mock_schedule_sheet,
            'Completed Sections RAW': mock_sections_sheet
        }[name]
        
        mock_render.return_value = 'rendered template'
        
        response = self.client.get(f'/home/{self.TEST_DATE_STR}/team/Red/kid/John%20Doe/section/1.1')
        self.assertEqual(response.status_code, 200)
        
        mock_render.assert_called_once()
        call_args = mock_render.call_args[1]
        self.assertEqual(call_args['kid_name'], 'John Doe')
        self.assertEqual(call_args['section_name'], '1.1')
    
    @patch('routes.home.spreadsheet')
    def test_submit_section_success(self, mock_spreadsheet):
        """Test submit_section with valid form data"""
        mock_sections_sheet = Mock()
        mock_sections_sheet.row_values.return_value = self.SAMPLE_HEADERS
        mock_sections_sheet.append_row = Mock()
        
        mock_spreadsheet.worksheet.return_value = mock_sections_sheet
        
        form_data = {
            'name': 'John Doe',
            'date': 'September 17, 2025',
            'team': 'Red',
            'date_str': self.TEST_DATE_STR,
            'section': '1.1',
            'Section Complete': 'on'
        }
        
        response = self.client.post('/submit_section', data=form_data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertIn(f'/home/{self.TEST_DATE_STR}/team/Red', response.location)
        
        # Verify append_row was called
        mock_sections_sheet.append_row.assert_called_once()
    
    @patch('routes.home.spreadsheet')
    def test_submit_section_error(self, mock_spreadsheet):
        """Test submit_section with sheet error"""
        mock_spreadsheet.worksheet.side_effect = Exception("Sheet error")
        
        form_data = {
            'name': 'John Doe',
            'date': 'September 17, 2025',
            'team': 'Red',
            'date_str': self.TEST_DATE_STR,
            'section': '1.1'
        }
        
        response = self.client.post('/submit_section', data=form_data)
        self.assertEqual(response.status_code, 302)  # Redirect to home on error
        self.assertIn('/', response.location)
    
    @patch('routes.home.spreadsheet')
    def test_edit_section_get_redirect(self, mock_spreadsheet):
        """Test edit_section GET request redirects to home"""
        response = self.client.get('/edit_section')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/', response.location)
    
    @patch('routes.home.spreadsheet')
    def test_edit_section_post_success(self, mock_spreadsheet):
        """Test edit_section POST with successful update"""
        mock_schedule_sheet = Mock()
        mock_schedule_sheet.get_all_records.return_value = self.SAMPLE_SCHEDULE_DATA
        
        mock_sections_sheet = Mock()
        mock_sections_sheet.get_all_records.return_value = [
            {'Date': 'September 17, 2025', 'Team': 'Red', 'Name': 'John Doe', 'Section': '1.1', 'Section Complete': False}
        ]
        mock_sections_sheet.row_values.return_value = ['Date', 'Team', 'Name', 'Section', 'Section Complete']
        mock_sections_sheet.update_cell = Mock()
        
        mock_spreadsheet.worksheet.side_effect = lambda name: {
            'Schedule': mock_schedule_sheet,
            'Completed Sections RAW': mock_sections_sheet
        }[name]
        
        form_data = {
            'date_str': self.TEST_DATE_STR,
            'team_name': 'Red',
            'kid_name': 'John Doe',
            'section_name': '1.1',
            'Section Complete': 'on'
        }
        
        response = self.client.post('/edit_section', data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'/home/{self.TEST_DATE_STR}/team/Red/kid/John%20Doe/section/1.1', response.location)
        
        # Verify update_cell was called
        mock_sections_sheet.update_cell.assert_called()
    
    @patch('routes.home.spreadsheet')
    def test_edit_section_post_invalid_date(self, mock_spreadsheet):
        """Test edit_section POST with invalid date"""
        mock_schedule_sheet = Mock()
        mock_schedule_sheet.get_all_records.return_value = self.SAMPLE_SCHEDULE_DATA
        mock_spreadsheet.worksheet.return_value = mock_schedule_sheet
        
        form_data = {
            'date_str': '2025-12-25',  # Invalid date not in schedule
            'team_name': 'Red',
            'kid_name': 'John Doe',
            'section_name': '1.1'
        }
        
        response = self.client.post('/edit_section', data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/', response.location)
    
    @patch('routes.home.spreadsheet')
    def test_edit_section_post_no_match(self, mock_spreadsheet):
        """Test edit_section POST when no matching entry is found"""
        mock_schedule_sheet = Mock()
        mock_schedule_sheet.get_all_records.return_value = self.SAMPLE_SCHEDULE_DATA
        
        mock_sections_sheet = Mock()
        mock_sections_sheet.get_all_records.return_value = []  # No matching entries
        
        mock_spreadsheet.worksheet.side_effect = lambda name: {
            'Schedule': mock_schedule_sheet,
            'Completed Sections RAW': mock_sections_sheet
        }[name]
        
        form_data = {
            'date_str': self.TEST_DATE_STR,
            'team_name': 'Red',
            'kid_name': 'John Doe',
            'section_name': '1.1'
        }
        
        response = self.client.post('/edit_section', data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'/home/{self.TEST_DATE_STR}/team/Red/kid/John%20Doe/section/1.1', response.location)
    
    @patch('routes.home.spreadsheet')
    def test_edit_section_post_error(self, mock_spreadsheet):
        """Test edit_section POST with sheet error"""
        mock_spreadsheet.worksheet.side_effect = Exception("Sheet error")
        
        form_data = {
            'date_str': self.TEST_DATE_STR,
            'team_name': 'Red',
            'kid_name': 'John Doe',
            'section_name': '1.1'
        }
        
        response = self.client.post('/edit_section', data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/', response.location)


if __name__ == '__main__':
    unittest.main()