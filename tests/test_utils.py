import unittest
from unittest.mock import Mock
from datetime import datetime
import sys
import os

# Add the parent directory to Python path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import functions to test
from models.utils import dates_match, find_column_index, parse_date_string, find_day_by_date, date_to_url, url_to_date

class TestUtilityFunctions(unittest.TestCase):
    
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
    
    def test_find_day_by_date_found(self):
        """Test find_day_by_date when date is found"""
        schedule_data = [
            {'Date': 'September 17, 2025', 'Theme': 'Test Theme 1'},
            {'Date': 'September 18, 2025', 'Theme': 'Test Theme 2'}
        ]
        result = find_day_by_date(schedule_data, 'September 17, 2025')
        self.assertEqual(result['Theme'], 'Test Theme 1')
    
    def test_find_day_by_date_not_found(self):
        """Test find_day_by_date when date is not found"""
        schedule_data = [
            {'Date': 'September 17, 2025', 'Theme': 'Test Theme 1'}
        ]
        result = find_day_by_date(schedule_data, 'December 25, 2025')
        self.assertIsNone(result)
    
    def test_date_to_url_readable_format(self):
        """Test date_to_url with readable format"""
        result = date_to_url('September 17, 2025')
        self.assertEqual(result, '2025-09-17')
    
    def test_date_to_url_already_url_format(self):
        """Test date_to_url with already URL format"""
        result = date_to_url('2025-09-17')
        self.assertEqual(result, '2025-09-17')
    
    def test_date_to_url_invalid_format(self):
        """Test date_to_url with invalid format returns as-is"""
        result = date_to_url('invalid-date')
        self.assertEqual(result, 'invalid-date')
    
    def test_url_to_date_valid_format(self):
        """Test url_to_date with valid URL format"""
        result = url_to_date('2025-09-17')
        self.assertEqual(result, 'September 17, 2025')
    
    def test_date_to_url_iso_format(self):
        """Test date_to_url with ISO format"""
        result = date_to_url('2025-09-17T00:00:00.000Z')
        self.assertEqual(result, '2025-09-17')
    
    def test_url_to_date_invalid_format(self):
        """Test url_to_date with invalid format returns as-is"""
        result = url_to_date('invalid-date')
        self.assertEqual(result, 'invalid-date')
    
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

if __name__ == '__main__':
    unittest.main(verbosity=2)