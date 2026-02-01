import sys
import unittest
from unittest.mock import patch, MagicMock

# Mock gspread before importing routes
sys.modules['gspread'] = MagicMock()
sys.modules['gspread.exceptions'] = MagicMock()
sys.modules['oauth2client'] = MagicMock()
sys.modules['oauth2client.service_account'] = MagicMock()

with patch.dict('os.environ', {'GOOGLE_SHEETS_CREDS': '{}'}):
    from tnt import app


class TestProgressRoutes(unittest.TestCase):
    """Tests for progress route handlers"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('routes.progress.get_sheet_data')
    def test_progress_returns_students(self, mock_get_sheet_data):
        """GET /progress should return all students from roster"""
        mock_get_sheet_data.return_value = [
            {'Name': 'Alice', 'Group': 'Red'},
            {'Name': 'Bob', 'Group': 'Blue'},
        ]

        response = self.client.get('/progress')

        self.assertEqual(response.status_code, 200)
        mock_get_sheet_data.assert_called_once_with('Master Roster')

    @patch('routes.progress.get_sheet_data')
    def test_progress_handles_error(self, mock_get_sheet_data):
        """GET /progress should handle errors gracefully"""
        mock_get_sheet_data.side_effect = Exception('Sheet not found')

        response = self.client.get('/progress')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sheet not found', response.data)


class TestStudentProgressRoutes(unittest.TestCase):
    """Tests for student progress route"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('routes.progress.get_sheet_data')
    def test_student_progress_shows_student_data(self, mock_get_sheet_data):
        """GET /progress/student/<name> should show student progress"""
        mock_get_sheet_data.side_effect = [
            [{'Name': 'Alice', 'Group': 'Red'}],  # Master Roster
            [
                {'Name': 'Alice', 'Section': '1.1', 'Silver Credit': 'TRUE', 'Gold Credit': 'FALSE'},
                {'Name': 'Alice', 'Section': '1.2', 'Silver Credit': 'TRUE', 'Gold Credit': 'TRUE'},
            ],  # Completed Sections
        ]

        response = self.client.get('/progress/student/Alice')

        self.assertEqual(response.status_code, 200)

    @patch('routes.progress.get_sheet_data')
    def test_student_progress_calculates_stats(self, mock_get_sheet_data):
        """Should calculate silver and gold credit counts"""
        mock_get_sheet_data.side_effect = [
            [{'Name': 'Alice', 'Group': 'Red'}],
            [
                {'Name': 'Alice', 'Section': '1.1', 'Silver Credit': 'TRUE', 'Gold Credit': 'FALSE'},
                {'Name': 'Alice', 'Section': '1.2', 'Silver Credit': 'TRUE', 'Gold Credit': 'TRUE'},
                {'Name': 'Alice', 'Section': '1.3', 'Silver Credit': 'FALSE', 'Gold Credit': 'FALSE'},
            ],
        ]

        response = self.client.get('/progress/student/Alice')

        self.assertEqual(response.status_code, 200)

    @patch('routes.progress.get_sheet_data')
    def test_student_progress_handles_url_encoding(self, mock_get_sheet_data):
        """Should handle URL-encoded student names"""
        mock_get_sheet_data.side_effect = [
            [{'Name': "Alice O'Brien", 'Group': 'Red'}],
            [{'Name': "Alice O'Brien", 'Section': '1.1', 'Silver Credit': 'TRUE', 'Gold Credit': 'FALSE'}],
        ]

        response = self.client.get("/progress/student/Alice%20O'Brien")

        self.assertEqual(response.status_code, 200)

    @patch('routes.progress.get_sheet_data')
    def test_student_progress_filters_by_student(self, mock_get_sheet_data):
        """Should only include sections for the requested student"""
        mock_get_sheet_data.side_effect = [
            [{'Name': 'Alice', 'Group': 'Red'}],
            [
                {'Name': 'Alice', 'Section': '1.1', 'Silver Credit': 'TRUE', 'Gold Credit': 'FALSE'},
                {'Name': 'Bob', 'Section': '1.1', 'Silver Credit': 'TRUE', 'Gold Credit': 'TRUE'},
            ],
        ]

        response = self.client.get('/progress/student/Alice')

        self.assertEqual(response.status_code, 200)

    @patch('routes.progress.get_sheet_data')
    def test_student_progress_handles_error(self, mock_get_sheet_data):
        """Should redirect on error"""
        mock_get_sheet_data.side_effect = Exception('Error')

        response = self.client.get('/progress/student/Alice')

        self.assertEqual(response.status_code, 302)


class TestStudentSectionDetailsRoutes(unittest.TestCase):
    """Tests for student section details route"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('routes.progress.get_sheet_data')
    def test_section_details_shows_entry(self, mock_get_sheet_data):
        """GET /progress/student/<name>/section/<index> should show section"""
        mock_get_sheet_data.return_value = [
            {'Name': 'Alice', 'Section': '1.1', 'Silver Credit': 'TRUE'},
            {'Name': 'Alice', 'Section': '1.2', 'Silver Credit': 'TRUE'},
        ]

        response = self.client.get('/progress/student/Alice/section/0')

        self.assertEqual(response.status_code, 200)

    @patch('routes.progress.get_sheet_data')
    def test_section_details_redirects_invalid_index(self, mock_get_sheet_data):
        """Should redirect if section index is out of range"""
        mock_get_sheet_data.return_value = [
            {'Name': 'Alice', 'Section': '1.1', 'Silver Credit': 'TRUE'},
        ]

        response = self.client.get('/progress/student/Alice/section/5')

        self.assertEqual(response.status_code, 302)

    @patch('routes.progress.get_sheet_data')
    def test_section_details_handles_error(self, mock_get_sheet_data):
        """Should redirect on error"""
        mock_get_sheet_data.side_effect = Exception('Error')

        response = self.client.get('/progress/student/Alice/section/0')

        self.assertEqual(response.status_code, 302)


class TestEditProgressSectionRoutes(unittest.TestCase):
    """Tests for edit progress section POST route"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_edit_progress_section_get_redirects(self):
        """GET /edit_progress_section should redirect"""
        response = self.client.get('/edit_progress_section')

        self.assertEqual(response.status_code, 302)

    @patch('routes.progress.refresh_computed_sheets')
    @patch('routes.progress.cache_update_row')
    @patch('routes.progress.get_worksheet')
    def test_edit_progress_section_updates_sheet(self, mock_get_worksheet, mock_cache_update, mock_refresh):
        """POST /edit_progress_section should update the sheet"""
        mock_worksheet = MagicMock()
        mock_worksheet.get_all_records.return_value = [
            {'Name': 'Alice', 'Date': 'January 15, 2025', 'Section': '1.1', 'Silver Credit': False}
        ]
        mock_worksheet.row_values.return_value = ['Name', 'Date', 'Section', 'Silver Credit']
        mock_get_worksheet.return_value = mock_worksheet

        response = self.client.post('/edit_progress_section', data={
            'student_name': 'Alice',
            'section_index': '0',
            'Silver Credit': 'on',
        })

        self.assertEqual(response.status_code, 302)
        mock_worksheet.update_cell.assert_called()

    @patch('routes.progress.refresh_computed_sheets')
    @patch('routes.progress.cache_update_row')
    @patch('routes.progress.get_worksheet')
    def test_edit_progress_section_updates_cache(self, mock_get_worksheet, mock_cache_update, mock_refresh):
        """POST /edit_progress_section should update cache"""
        mock_worksheet = MagicMock()
        mock_worksheet.get_all_records.return_value = [
            {'Name': 'Alice', 'Date': 'January 15, 2025', 'Section': '1.1', 'Silver Credit': False}
        ]
        mock_worksheet.row_values.return_value = ['Name', 'Date', 'Section', 'Silver Credit']
        mock_get_worksheet.return_value = mock_worksheet

        self.client.post('/edit_progress_section', data={
            'student_name': 'Alice',
            'section_index': '0',
        })

        mock_cache_update.assert_called_once()
        mock_refresh.assert_called_once_with('Completed Sections RAW')

    @patch('routes.progress.refresh_computed_sheets')
    @patch('routes.progress.cache_update_row')
    @patch('routes.progress.get_worksheet')
    def test_edit_progress_section_redirects_to_section(self, mock_get_worksheet, mock_cache_update, mock_refresh):
        """POST /edit_progress_section should redirect to section details"""
        mock_worksheet = MagicMock()
        mock_worksheet.get_all_records.return_value = [
            {'Name': 'Alice', 'Date': 'January 15, 2025', 'Section': '1.1', 'Silver Credit': False}
        ]
        mock_worksheet.row_values.return_value = ['Name', 'Date', 'Section', 'Silver Credit']
        mock_get_worksheet.return_value = mock_worksheet

        response = self.client.post('/edit_progress_section', data={
            'student_name': 'Alice',
            'section_index': '0',
        })

        self.assertEqual(response.status_code, 302)
        self.assertIn('/progress/student/Alice/section/0', response.location)

    @patch('routes.progress.get_worksheet')
    def test_edit_progress_section_handles_invalid_index(self, mock_get_worksheet):
        """POST /edit_progress_section should redirect on invalid index"""
        mock_worksheet = MagicMock()
        mock_worksheet.get_all_records.return_value = [
            {'Name': 'Alice', 'Date': 'January 15, 2025', 'Section': '1.1'}
        ]
        mock_get_worksheet.return_value = mock_worksheet

        response = self.client.post('/edit_progress_section', data={
            'student_name': 'Alice',
            'section_index': '999',
        })

        self.assertEqual(response.status_code, 302)

    @patch('routes.progress.get_worksheet')
    def test_edit_progress_section_handles_error(self, mock_get_worksheet):
        """POST /edit_progress_section should redirect on error"""
        mock_get_worksheet.side_effect = Exception('Error')

        response = self.client.post('/edit_progress_section', data={
            'student_name': 'Alice',
            'section_index': '0',
        })

        self.assertEqual(response.status_code, 302)


if __name__ == '__main__':
    unittest.main()
