import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to Python path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from routes.progress import register_progress_routes

class TestProgressRoutes(unittest.TestCase):
    
    # Common test data
    SAMPLE_ROSTER_DATA = [
        {'Name': 'John Doe', 'Group': 'Red'},
        {'Name': 'Jane Smith', 'Group': 'Blue'}
    ]
    
    SAMPLE_SECTIONS_DATA = [
        {'Name': 'John Doe', 'Date': 'September 17, 2025', 'Section': '1.1', 'Silver Credit': 'TRUE', 'Gold Credit': 'FALSE'},
        {'Name': 'John Doe', 'Date': 'September 18, 2025', 'Section': '1.2', 'Silver Credit': 'FALSE', 'Gold Credit': 'TRUE'},
        {'Name': 'Jane Smith', 'Date': 'September 17, 2025', 'Section': '2.1', 'Silver Credit': 'TRUE', 'Gold Credit': 'TRUE'}
    ]
    
    SAMPLE_HEADERS = ['Name', 'Date', 'Section', 'Silver Credit', 'Gold Credit', 'Section Complete']
    
    def setUp(self):
        """Set up test Flask app with progress routes"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
        register_progress_routes(self.app)
        self.client = self.app.test_client()
    
    def create_mock_sheets(self, roster_data=None, sections_data=None):
        """Helper method to create mock sheets with data"""
        mock_roster_sheet = Mock()
        mock_roster_sheet.get_all_records.return_value = roster_data or self.SAMPLE_ROSTER_DATA
        
        mock_sections_sheet = Mock()
        mock_sections_sheet.get_all_records.return_value = sections_data or self.SAMPLE_SECTIONS_DATA
        
        return mock_roster_sheet, mock_sections_sheet
    
    @patch('routes.progress.render_template')
    @patch('routes.progress.spreadsheet')
    def test_progress_route_success(self, mock_spreadsheet, mock_render):
        """Test progress route with successful data retrieval"""
        mock_roster_sheet, _ = self.create_mock_sheets()
        mock_spreadsheet.worksheet.return_value = mock_roster_sheet
        mock_render.return_value = 'rendered template'
        
        response = self.client.get('/progress')
        self.assertEqual(response.status_code, 200)
        
        mock_render.assert_called_once_with(
            'progress.html',
            students=self.SAMPLE_ROSTER_DATA
        )
    
    @patch('routes.progress.render_template')
    @patch('routes.progress.spreadsheet')
    def test_progress_route_error(self, mock_spreadsheet, mock_render):
        """Test progress route with sheet access error"""
        mock_spreadsheet.worksheet.side_effect = Exception("Sheet not found")
        mock_render.return_value = 'rendered template'
        
        response = self.client.get('/progress')
        self.assertEqual(response.status_code, 200)
        
        mock_render.assert_called_once_with(
            'progress.html',
            students=[],
            error="Sheet not found"
        )
    
    @patch('routes.progress.render_template')
    @patch('routes.progress.spreadsheet')
    def test_student_progress_success(self, mock_spreadsheet, mock_render):
        """Test student_progress with valid student name"""
        mock_roster_sheet, mock_sections_sheet = self.create_mock_sheets()
        
        mock_spreadsheet.worksheet.side_effect = lambda name: {
            'Master Roster': mock_roster_sheet,
            'Completed Sections RAW': mock_sections_sheet
        }[name]
        
        mock_render.return_value = 'rendered template'
        
        response = self.client.get('/progress/student/John%20Doe')
        self.assertEqual(response.status_code, 200)
        
        mock_render.assert_called_once()
        call_args = mock_render.call_args[1]
        self.assertEqual(call_args['student_name'], 'John Doe')
        self.assertEqual(call_args['total_sections'], 2)  # John has 2 sections
        self.assertEqual(call_args['silver_earned'], 1)   # 1 silver credit
        self.assertEqual(call_args['gold_earned'], 1)     # 1 gold credit
    
    @patch('routes.progress.spreadsheet')
    def test_student_progress_invalid_student(self, mock_spreadsheet):
        """Test student_progress with invalid student name"""
        mock_roster_sheet, mock_sections_sheet = self.create_mock_sheets()
        
        mock_spreadsheet.worksheet.side_effect = lambda name: {
            'Master Roster': mock_roster_sheet,
            'Completed Sections RAW': mock_sections_sheet
        }[name]
        
        response = self.client.get('/progress/student/NonExistent')
        self.assertEqual(response.status_code, 302)  # Redirect to progress
        self.assertIn('/progress', response.location)
    
    @patch('routes.progress.spreadsheet')
    def test_student_progress_sheet_error(self, mock_spreadsheet):
        """Test student_progress with sheet access error"""
        mock_spreadsheet.worksheet.side_effect = Exception("Sheet error")
        
        response = self.client.get('/progress/student/John%20Doe')
        self.assertEqual(response.status_code, 302)  # Redirect to progress
        self.assertIn('/progress', response.location)
    
    @patch('routes.progress.render_template')
    @patch('routes.progress.spreadsheet')
    def test_student_section_details_success(self, mock_spreadsheet, mock_render):
        """Test student_section_details with valid parameters"""
        _, mock_sections_sheet = self.create_mock_sheets()
        mock_spreadsheet.worksheet.return_value = mock_sections_sheet
        mock_render.return_value = 'rendered template'
        
        response = self.client.get('/progress/student/John%20Doe/section/0')
        self.assertEqual(response.status_code, 200)
        
        mock_render.assert_called_once()
        call_args = mock_render.call_args[1]
        self.assertEqual(call_args['student_name'], 'John Doe')
        self.assertEqual(call_args['section_index'], 0)
        self.assertEqual(call_args['section_entry']['Section'], '1.1')
    
    @patch('routes.progress.spreadsheet')
    def test_student_section_details_invalid_index(self, mock_spreadsheet):
        """Test student_section_details with invalid section index"""
        _, mock_sections_sheet = self.create_mock_sheets()
        mock_spreadsheet.worksheet.return_value = mock_sections_sheet
        
        # Test with index out of range
        response = self.client.get('/progress/student/John%20Doe/section/99')
        self.assertEqual(response.status_code, 302)  # Redirect to student progress
        self.assertIn('/progress/student/John%20Doe', response.location)
    
    @patch('routes.progress.spreadsheet')
    def test_student_section_details_sheet_error(self, mock_spreadsheet):
        """Test student_section_details with sheet access error"""
        mock_spreadsheet.worksheet.side_effect = Exception("Sheet error")
        
        response = self.client.get('/progress/student/John%20Doe/section/0')
        self.assertEqual(response.status_code, 302)  # Redirect to progress
        self.assertIn('/progress', response.location)
    
    @patch('routes.progress.spreadsheet')
    def test_edit_progress_section_get_redirect(self, mock_spreadsheet):
        """Test edit_progress_section GET request redirects to progress"""
        response = self.client.get('/edit_progress_section')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/progress', response.location)
    
    @patch('routes.progress.spreadsheet')
    def test_edit_progress_section_post_success(self, mock_spreadsheet):
        """Test edit_progress_section POST with successful update"""
        mock_sections_sheet = Mock()
        mock_sections_sheet.get_all_records.return_value = self.SAMPLE_SECTIONS_DATA
        mock_sections_sheet.row_values.return_value = self.SAMPLE_HEADERS
        mock_sections_sheet.update_cell = Mock()
        
        mock_spreadsheet.worksheet.return_value = mock_sections_sheet
        
        form_data = {
            'student_name': 'John Doe',
            'section_index': '0',
            'Silver Credit': 'on',
            'Section Complete': 'on'
        }
        
        response = self.client.post('/edit_progress_section', data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/progress/student/John%20Doe/section/0', response.location)
        
        # Verify update_cell was called
        mock_sections_sheet.update_cell.assert_called()
    
    @patch('routes.progress.spreadsheet')
    def test_edit_progress_section_post_invalid_index(self, mock_spreadsheet):
        """Test edit_progress_section POST with invalid section index"""
        mock_sections_sheet = Mock()
        mock_sections_sheet.get_all_records.return_value = self.SAMPLE_SECTIONS_DATA
        mock_spreadsheet.worksheet.return_value = mock_sections_sheet
        
        form_data = {
            'student_name': 'John Doe',
            'section_index': '99'  # Invalid index
        }
        
        response = self.client.post('/edit_progress_section', data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/progress', response.location)
    
    @patch('routes.progress.spreadsheet')
    def test_edit_progress_section_post_no_match(self, mock_spreadsheet):
        """Test edit_progress_section POST when no matching entry is found"""
        mock_sections_sheet = Mock()
        mock_sections_sheet.get_all_records.return_value = []  # No matching entries
        mock_spreadsheet.worksheet.return_value = mock_sections_sheet
        
        form_data = {
            'student_name': 'John Doe',
            'section_index': '0'
        }
        
        response = self.client.post('/edit_progress_section', data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/progress', response.location)
    
    @patch('routes.progress.spreadsheet')
    def test_edit_progress_section_post_error(self, mock_spreadsheet):
        """Test edit_progress_section POST with sheet error"""
        mock_spreadsheet.worksheet.side_effect = Exception("Sheet error")
        
        form_data = {
            'student_name': 'John Doe',
            'section_index': '0'
        }
        
        response = self.client.post('/edit_progress_section', data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/progress', response.location)
    
    @patch('routes.progress.render_template')
    @patch('routes.progress.spreadsheet')
    def test_student_progress_stats_calculation(self, mock_spreadsheet, mock_render):
        """Test that student progress correctly calculates silver and gold credits"""
        mock_roster_sheet, _ = self.create_mock_sheets()
        
        # Custom sections data for testing stats
        custom_sections = [
            {'Name': 'Test Student', 'Silver Credit': 'TRUE', 'Gold Credit': 'FALSE'},
            {'Name': 'Test Student', 'Silver Credit': 'yes', 'Gold Credit': 'TRUE'},
            {'Name': 'Test Student', 'Silver Credit': '1', 'Gold Credit': 'false'},
            {'Name': 'Test Student', 'Silver Credit': 'false', 'Gold Credit': '1'}
        ]
        
        mock_sections_sheet = Mock()
        mock_sections_sheet.get_all_records.return_value = custom_sections
        
        mock_spreadsheet.worksheet.side_effect = lambda name: {
            'Master Roster': mock_roster_sheet,
            'Completed Sections RAW': mock_sections_sheet
        }[name]
        
        mock_render.return_value = 'rendered template'
        
        response = self.client.get('/progress/student/Test%20Student')
        self.assertEqual(response.status_code, 200)
        
        mock_render.assert_called_once()
        call_args = mock_render.call_args[1]
        self.assertEqual(call_args['total_sections'], 4)
        self.assertEqual(call_args['silver_earned'], 3)  # TRUE, yes, 1
        self.assertEqual(call_args['gold_earned'], 2)    # TRUE, 1


if __name__ == '__main__':
    unittest.main()