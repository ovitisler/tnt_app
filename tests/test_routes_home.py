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


class TestHomeRoutes(unittest.TestCase):
    """Tests for home route handlers"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('routes.home.get_sheet_data')
    def test_home_returns_schedule_data(self, mock_get_sheet_data):
        """GET / should return schedule data"""
        mock_get_sheet_data.return_value = [
            {'Date': 'January 15, 2025', 'Theme': 'Test Theme'}
        ]

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        mock_get_sheet_data.assert_called_once_with('Schedule')

    @patch('routes.home.get_sheet_data')
    def test_home_handles_error(self, mock_get_sheet_data):
        """GET / should handle errors gracefully"""
        mock_get_sheet_data.side_effect = Exception('Sheet not found')

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sheet not found', response.data)


class TestHomeDetailsRoutes(unittest.TestCase):
    """Tests for home details route"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('routes.home.get_sheet_data')
    def test_home_details_shows_day_data(self, mock_get_sheet_data):
        """GET /home/<date_str> should show day details"""
        mock_get_sheet_data.side_effect = [
            [{'Date': 'January 15, 2025', 'Theme': 'Test Theme'}],  # Schedule
            [{'Date': 'January 15, 2025', 'Team': 'Red', 'Total': 10}],  # Weekly Totals
        ]

        response = self.client.get('/home/2025-01-15')

        self.assertEqual(response.status_code, 200)

    @patch('routes.home.get_sheet_data')
    def test_home_details_redirects_if_date_not_found(self, mock_get_sheet_data):
        """GET /home/<date_str> should redirect if date not in schedule"""
        mock_get_sheet_data.return_value = [
            {'Date': 'January 15, 2025', 'Theme': 'Test Theme'}
        ]

        response = self.client.get('/home/2025-12-31')

        self.assertEqual(response.status_code, 302)

    @patch('routes.home.get_sheet_data')
    def test_home_details_handles_error(self, mock_get_sheet_data):
        """GET /home/<date_str> should redirect on error"""
        mock_get_sheet_data.side_effect = Exception('Error')

        response = self.client.get('/home/2025-01-15')

        self.assertEqual(response.status_code, 302)


class TestHomeTeamDetailsRoutes(unittest.TestCase):
    """Tests for team details route"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('routes.home.get_sheet_data')
    def test_team_details_shows_team_data(self, mock_get_sheet_data):
        """GET /home/<date>/team/<team> should show team details"""
        mock_get_sheet_data.side_effect = [
            [{'Date': 'January 15, 2025', 'Theme': 'Test Theme'}],  # Schedule
            [{'Date': 'January 15, 2025', 'Team': 'Red', 'Total': 10}],  # Weekly Totals
            [{'Date': 'January 15, 2025', 'Team': 'Red', 'Name': 'Alice', 'Section': '1.1'}],  # Sections
        ]

        response = self.client.get('/home/2025-01-15/team/Red')

        self.assertEqual(response.status_code, 200)

    @patch('routes.home.get_sheet_data')
    def test_team_details_groups_sections_by_kid(self, mock_get_sheet_data):
        """Should group sections by kid name"""
        mock_get_sheet_data.side_effect = [
            [{'Date': 'January 15, 2025', 'Theme': 'Test'}],
            [{'Date': 'January 15, 2025', 'Team': 'Red', 'Total': 10}],
            [
                {'Date': 'January 15, 2025', 'Team': 'Red', 'Name': 'Alice', 'Section': '1.1'},
                {'Date': 'January 15, 2025', 'Team': 'Red', 'Name': 'Alice', 'Section': '1.2'},
                {'Date': 'January 15, 2025', 'Team': 'Red', 'Name': 'Bob', 'Section': '1.1'},
            ],
        ]

        response = self.client.get('/home/2025-01-15/team/Red')

        self.assertEqual(response.status_code, 200)

    @patch('routes.home.get_sheet_data')
    def test_team_details_redirects_if_date_not_found(self, mock_get_sheet_data):
        """Should redirect if date not in schedule"""
        mock_get_sheet_data.return_value = []

        response = self.client.get('/home/2025-01-15/team/Red')

        self.assertEqual(response.status_code, 302)


class TestRecordSectionFormRoutes(unittest.TestCase):
    """Tests for record section form route"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('routes.home.get_sheet_data')
    def test_record_section_form_shows_team_kids(self, mock_get_sheet_data):
        """GET /home/<date>/team/<team>/record_section should show form with team kids"""
        mock_get_sheet_data.side_effect = [
            [{'Date': 'January 15, 2025', 'Theme': 'Test'}],  # Schedule
            [{'Name': 'Alice', 'Group': 'Red'}, {'Name': 'Bob', 'Group': 'Blue'}],  # Master Roster
        ]

        response = self.client.get('/home/2025-01-15/team/Red/record_section')

        self.assertEqual(response.status_code, 200)

    @patch('routes.home.get_sheet_data')
    def test_record_section_form_redirects_if_date_not_found(self, mock_get_sheet_data):
        """Should redirect if date not in schedule"""
        mock_get_sheet_data.return_value = []

        response = self.client.get('/home/2025-01-15/team/Red/record_section')

        self.assertEqual(response.status_code, 302)


class TestSubmitSectionRoutes(unittest.TestCase):
    """Tests for submit section POST route"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('routes.home.refresh_computed_sheets')
    @patch('routes.home.cache_append_row')
    @patch('routes.home.get_worksheet')
    def test_submit_section_writes_to_sheet(self, mock_get_worksheet, mock_cache_append, mock_refresh):
        """POST /submit_section should write to Google Sheets"""
        mock_worksheet = MagicMock()
        mock_worksheet.row_values.return_value = ['timestamp', 'Name', 'Team', 'Date', 'Section', 'Section Complete', 'Silver Credit', 'Gold Credit']
        mock_get_worksheet.return_value = mock_worksheet

        response = self.client.post('/submit_section', data={
            'name': 'Alice',
            'team': 'Red',
            'date': 'January 15, 2025',
            'date_str': '2025-01-15',
            'section': '1.1',
        })

        self.assertEqual(response.status_code, 302)
        mock_worksheet.append_row.assert_called_once()

    @patch('routes.home.refresh_computed_sheets')
    @patch('routes.home.cache_append_row')
    @patch('routes.home.get_worksheet')
    def test_submit_section_updates_cache(self, mock_get_worksheet, mock_cache_append, mock_refresh):
        """POST /submit_section should update cache"""
        mock_worksheet = MagicMock()
        mock_worksheet.row_values.return_value = ['timestamp', 'Name', 'Team', 'Date', 'Section']
        mock_get_worksheet.return_value = mock_worksheet

        self.client.post('/submit_section', data={
            'name': 'Alice',
            'team': 'Red',
            'date': 'January 15, 2025',
            'date_str': '2025-01-15',
            'section': '1.1',
        })

        mock_cache_append.assert_called_once()
        call_args = mock_cache_append.call_args[0]
        self.assertEqual(call_args[0], 'Completed Sections RAW')
        self.assertEqual(call_args[1]['Name'], 'Alice')

    @patch('routes.home.refresh_computed_sheets')
    @patch('routes.home.cache_append_row')
    @patch('routes.home.get_worksheet')
    def test_submit_section_triggers_refresh(self, mock_get_worksheet, mock_cache_append, mock_refresh):
        """POST /submit_section should trigger computed sheets refresh"""
        mock_worksheet = MagicMock()
        mock_worksheet.row_values.return_value = ['timestamp', 'Name', 'Team', 'Date', 'Section']
        mock_get_worksheet.return_value = mock_worksheet

        self.client.post('/submit_section', data={
            'name': 'Alice',
            'team': 'Red',
            'date': 'January 15, 2025',
            'date_str': '2025-01-15',
            'section': '1.1',
        })

        mock_refresh.assert_called_once_with('Completed Sections RAW')

    @patch('routes.home.refresh_computed_sheets')
    @patch('routes.home.cache_append_row')
    @patch('routes.home.get_worksheet')
    def test_submit_section_redirects_to_team_page(self, mock_get_worksheet, mock_cache_append, mock_refresh):
        """POST /submit_section should redirect to team page"""
        mock_worksheet = MagicMock()
        mock_worksheet.row_values.return_value = ['timestamp', 'Name', 'Team', 'Date', 'Section']
        mock_get_worksheet.return_value = mock_worksheet

        response = self.client.post('/submit_section', data={
            'name': 'Alice',
            'team': 'Red',
            'date': 'January 15, 2025',
            'date_str': '2025-01-15',
            'section': '1.1',
        })

        self.assertEqual(response.status_code, 302)
        self.assertIn('/home/2025-01-15/team/Red', response.location)

    @patch('routes.home.get_worksheet')
    def test_submit_section_handles_error(self, mock_get_worksheet):
        """POST /submit_section should redirect on error"""
        mock_get_worksheet.side_effect = Exception('Error')

        response = self.client.post('/submit_section', data={
            'name': 'Alice',
            'team': 'Red',
            'date': 'January 15, 2025',
            'date_str': '2025-01-15',
            'section': '1.1',
        })

        self.assertEqual(response.status_code, 302)


class TestEditSectionRoutes(unittest.TestCase):
    """Tests for edit section POST route"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_edit_section_get_redirects(self):
        """GET /edit_section should redirect"""
        response = self.client.get('/edit_section')

        self.assertEqual(response.status_code, 302)

    @patch('routes.home.refresh_computed_sheets')
    @patch('routes.home.cache_update_row')
    @patch('routes.home.get_worksheet')
    @patch('routes.home.get_sheet_data')
    def test_edit_section_updates_sheet(self, mock_get_sheet_data, mock_get_worksheet, mock_cache_update, mock_refresh):
        """POST /edit_section should update the sheet"""
        mock_get_sheet_data.return_value = [{'Date': 'January 15, 2025', 'Theme': 'Test'}]

        mock_worksheet = MagicMock()
        mock_worksheet.get_all_records.return_value = [
            {'Date': 'January 15, 2025', 'Team': 'Red', 'Name': 'Alice', 'Section': '1.1', 'Section Complete': False}
        ]
        mock_worksheet.row_values.return_value = ['Date', 'Team', 'Name', 'Section', 'Section Complete']
        mock_get_worksheet.return_value = mock_worksheet

        response = self.client.post('/edit_section', data={
            'date_str': '2025-01-15',
            'team_name': 'Red',
            'kid_name': 'Alice',
            'section_name': '1.1',
            'Section Complete': 'on',
        })

        self.assertEqual(response.status_code, 302)
        mock_worksheet.update_cell.assert_called()

    @patch('routes.home.refresh_computed_sheets')
    @patch('routes.home.cache_update_row')
    @patch('routes.home.get_worksheet')
    @patch('routes.home.get_sheet_data')
    def test_edit_section_updates_cache(self, mock_get_sheet_data, mock_get_worksheet, mock_cache_update, mock_refresh):
        """POST /edit_section should update cache"""
        mock_get_sheet_data.return_value = [{'Date': 'January 15, 2025', 'Theme': 'Test'}]

        mock_worksheet = MagicMock()
        mock_worksheet.get_all_records.return_value = [
            {'Date': 'January 15, 2025', 'Team': 'Red', 'Name': 'Alice', 'Section': '1.1', 'Section Complete': False}
        ]
        mock_worksheet.row_values.return_value = ['Date', 'Team', 'Name', 'Section', 'Section Complete']
        mock_get_worksheet.return_value = mock_worksheet

        self.client.post('/edit_section', data={
            'date_str': '2025-01-15',
            'team_name': 'Red',
            'kid_name': 'Alice',
            'section_name': '1.1',
        })

        mock_cache_update.assert_called_once()
        mock_refresh.assert_called_once_with('Completed Sections RAW')


class TestHomeSectionDetailsRoutes(unittest.TestCase):
    """Tests for section details route"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('routes.home.get_sheet_data')
    def test_section_details_shows_entry(self, mock_get_sheet_data):
        """GET section details should show section entry"""
        mock_get_sheet_data.side_effect = [
            [{'Date': 'January 15, 2025', 'Theme': 'Test'}],  # Schedule
            [{'Date': 'January 15, 2025', 'Team': 'Red', 'Name': 'Alice', 'Section': '1.1'}],  # Sections
        ]

        response = self.client.get('/home/2025-01-15/team/Red/kid/Alice/section/1.1')

        self.assertEqual(response.status_code, 200)

    @patch('routes.home.get_sheet_data')
    def test_section_details_handles_url_encoding(self, mock_get_sheet_data):
        """Should handle URL-encoded kid names"""
        mock_get_sheet_data.side_effect = [
            [{'Date': 'January 15, 2025', 'Theme': 'Test'}],
            [{'Date': 'January 15, 2025', 'Team': 'Red', 'Name': "Alice O'Brien", 'Section': '1.1'}],
        ]

        response = self.client.get("/home/2025-01-15/team/Red/kid/Alice%20O'Brien/section/1.1")

        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
