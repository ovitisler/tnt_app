import unittest
from unittest.mock import Mock, patch
from datetime import datetime
import sys
import os

# Add the current directory to Python path so we can import tnt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import functions to test
from tnt import dates_match, find_column_index, parse_date_string

class TestTNTFunctions(unittest.TestCase):
    
    def test_dates_match_iso_format(self):
        """Test dates_match with ISO format dates"""
        date1 = "2025-09-17T00:00:00.000Z"
        date2 = "September 17, 2025"
        self.assertTrue(dates_match(date1, date2))
    
    def test_dates_match_readable_format(self):
        """Test dates_match with readable format dates"""
        date1 = "September 17, 2025"
        date2 = "September 17, 2025"
        self.assertTrue(dates_match(date1, date2))
    
    def test_dates_match_different_dates(self):
        """Test dates_match with different dates"""
        date1 = "September 17, 2025"
        date2 = "September 18, 2025"
        self.assertFalse(dates_match(date1, date2))
    
    def test_dates_match_empty_dates(self):
        """Test dates_match with empty/None dates"""
        self.assertFalse(dates_match(None, "September 17, 2025"))
        self.assertFalse(dates_match("September 17, 2025", None))
        self.assertFalse(dates_match("", "September 17, 2025"))
    
    def test_dates_match_invalid_format_fallback(self):
        """Test dates_match falls back to string comparison for invalid formats"""
        date1 = "invalid date"
        date2 = "invalid date"
        self.assertTrue(dates_match(date1, date2))
        
        date3 = "invalid date 1"
        date4 = "invalid date 2"
        self.assertFalse(dates_match(date3, date4))
    
    def test_find_column_index_found(self):
        """Test find_column_index when header is found"""
        mock_worksheet = Mock()
        mock_worksheet.row_values.return_value = ['Name', 'Team', 'Date', 'Present']
        
        result = find_column_index(mock_worksheet, 'Team')
        self.assertEqual(result, 2)  # 1-based index
    
    def test_find_column_index_not_found(self):
        """Test find_column_index when header is not found"""
        mock_worksheet = Mock()
        mock_worksheet.row_values.return_value = ['Name', 'Team', 'Date', 'Present']
        
        result = find_column_index(mock_worksheet, 'NonExistent')
        self.assertIsNone(result)
    
    def test_find_column_index_first_column(self):
        """Test find_column_index for first column"""
        mock_worksheet = Mock()
        mock_worksheet.row_values.return_value = ['Name', 'Team', 'Date', 'Present']
        
        result = find_column_index(mock_worksheet, 'Name')
        self.assertEqual(result, 1)  # 1-based index
    
    def test_parse_date_string_iso_format(self):
        """Test parse_date_string with ISO format"""
        from datetime import date
        result = parse_date_string("2025-09-17T00:00:00.000Z")
        expected = date(2025, 9, 17)
        self.assertEqual(result, expected)
    
    def test_parse_date_string_readable_format(self):
        """Test parse_date_string with readable format"""
        from datetime import date
        result = parse_date_string("September 17, 2025")
        expected = date(2025, 9, 17)
        self.assertEqual(result, expected)

class TestFlaskRoutes(unittest.TestCase):
    
    def setUp(self):
        """Set up test client"""
        from tnt import app
        self.app = app
        self.client = app.test_client()
    
    def test_static_files_route(self):
        """Test static files route returns correct status"""
        # Test accessing a static file (CSS)
        response = self.client.get('/static/style.css')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/css', response.content_type)
    
    def test_static_files_not_found(self):
        """Test static files route with non-existent file"""
        response = self.client.get('/static/nonexistent.css')
        self.assertEqual(response.status_code, 404)
    
    @patch('tnt.spreadsheet')
    def test_home_route_success(self, mock_spreadsheet):
        """Test home route with successful data retrieval"""
        # Mock the worksheet and data
        mock_worksheet = Mock()
        mock_worksheet.get_all_records.return_value = [
            {'Date': 'September 17, 2025', 'Theme': 'Test Theme'}
        ]
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        
        # Import app after mocking
        from tnt import app
        with app.test_client() as client:
            response = client.get('/')
            self.assertEqual(response.status_code, 200)
    
    @patch('tnt.spreadsheet')
    def test_home_route_error(self, mock_spreadsheet):
        """Test home route with error handling"""
        # Mock an exception
        mock_spreadsheet.worksheet.side_effect = Exception("Sheet not found")
        
        from tnt import app
        with app.test_client() as client:
            response = client.get('/')
            self.assertEqual(response.status_code, 200)  # Should still return 200 with error handling

if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)