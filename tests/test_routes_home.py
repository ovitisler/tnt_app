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

    @patch('routes.home.get_schedule')
    def test_home_returns_schedule_data(self, mock_get_schedule):
        """GET / should return schedule data"""
        mock_get_schedule.return_value = [
            {'Date': 'January 15, 2025', 'Theme': 'Test Theme'}
        ]

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        mock_get_schedule.assert_called_once()

    @patch('routes.home.get_schedule')
    def test_home_handles_error(self, mock_get_schedule):
        """GET / should handle errors gracefully"""
        mock_get_schedule.side_effect = Exception('Sheet not found')

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sheet not found', response.data)


class TestHomeDetailsRoutes(unittest.TestCase):
    """Tests for home details route"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('routes.home.get_weekly_totals')
    @patch('routes.home.get_schedule')
    def test_home_details_shows_day_data(self, mock_get_schedule, mock_get_totals):
        """GET /home/<date_str> should show day details"""
        mock_get_schedule.return_value = [
            {'Date': 'January 15, 2025', 'Theme': 'Test Theme'}
        ]
        mock_get_totals.return_value = [
            {'Date': 'January 15, 2025', 'Team': 'Red', 'Total': 10}
        ]

        response = self.client.get('/home/2025-01-15')

        self.assertEqual(response.status_code, 200)

    @patch('routes.home.get_schedule')
    def test_home_details_redirects_if_date_not_found(self, mock_get_schedule):
        """GET /home/<date_str> should redirect if date not in schedule"""
        mock_get_schedule.return_value = [
            {'Date': 'January 15, 2025', 'Theme': 'Test Theme'}
        ]

        response = self.client.get('/home/2025-12-31')

        self.assertEqual(response.status_code, 302)

    @patch('routes.home.get_schedule')
    def test_home_details_handles_error(self, mock_get_schedule):
        """GET /home/<date_str> should redirect on error"""
        mock_get_schedule.side_effect = Exception('Error')

        response = self.client.get('/home/2025-01-15')

        self.assertEqual(response.status_code, 302)


class TestHomeTeamDetailsRoutes(unittest.TestCase):
    """Tests for team details route"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('routes.home.get_completed_sections')
    @patch('routes.home.get_weekly_totals')
    @patch('routes.home.get_schedule')
    def test_team_details_shows_team_data(self, mock_get_schedule, mock_get_totals, mock_get_sections):
        """GET /home/<date>/team/<team> should show team details"""
        mock_get_schedule.return_value = [
            {'Date': 'January 15, 2025', 'Theme': 'Test Theme'}
        ]
        mock_get_totals.return_value = [
            {'Date': 'January 15, 2025', 'Team': 'Red', 'Total': 10}
        ]
        mock_get_sections.return_value = [
            {'Date': 'January 15, 2025', 'Team': 'Red', 'Name': 'Alice', 'Section': '1.1'}
        ]

        response = self.client.get('/home/2025-01-15/team/Red')

        self.assertEqual(response.status_code, 200)

    @patch('routes.home.get_completed_sections')
    @patch('routes.home.get_weekly_totals')
    @patch('routes.home.get_schedule')
    def test_team_details_groups_sections_by_kid(self, mock_get_schedule, mock_get_totals, mock_get_sections):
        """Should group sections by kid name"""
        mock_get_schedule.return_value = [
            {'Date': 'January 15, 2025', 'Theme': 'Test'}
        ]
        mock_get_totals.return_value = [
            {'Date': 'January 15, 2025', 'Team': 'Red', 'Total': 10}
        ]
        mock_get_sections.return_value = [
            {'Date': 'January 15, 2025', 'Team': 'Red', 'Name': 'Alice', 'Section': '1.1'},
            {'Date': 'January 15, 2025', 'Team': 'Red', 'Name': 'Alice', 'Section': '1.2'},
            {'Date': 'January 15, 2025', 'Team': 'Red', 'Name': 'Bob', 'Section': '1.1'},
        ]

        response = self.client.get('/home/2025-01-15/team/Red')

        self.assertEqual(response.status_code, 200)

    @patch('routes.home.get_schedule')
    def test_team_details_redirects_if_date_not_found(self, mock_get_schedule):
        """Should redirect if date not in schedule"""
        mock_get_schedule.return_value = []

        response = self.client.get('/home/2025-01-15/team/Red')

        self.assertEqual(response.status_code, 302)


class TestRecordSectionFormRoutes(unittest.TestCase):
    """Tests for record section form route"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('routes.home.get_roster')
    @patch('routes.home.get_schedule')
    def test_record_section_form_shows_team_kids(self, mock_get_schedule, mock_get_roster):
        """GET /home/<date>/team/<team>/record_section should show form with team kids"""
        mock_get_schedule.return_value = [
            {'Date': 'January 15, 2025', 'Theme': 'Test'}
        ]
        mock_get_roster.return_value = [
            {'Name': 'Alice', 'Group': 'Red'},
            {'Name': 'Bob', 'Group': 'Blue'}
        ]

        response = self.client.get('/home/2025-01-15/team/Red/record_section')

        self.assertEqual(response.status_code, 200)

    @patch('routes.home.get_schedule')
    def test_record_section_form_redirects_if_date_not_found(self, mock_get_schedule):
        """Should redirect if date not in schedule"""
        mock_get_schedule.return_value = []

        response = self.client.get('/home/2025-01-15/team/Red/record_section')

        self.assertEqual(response.status_code, 302)


class TestSubmitSectionRoutes(unittest.TestCase):
    """Tests for submit section POST route"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('routes.home.insert_completed_section')
    def test_submit_section_inserts_record(self, mock_insert):
        """POST /submit_section should insert a record"""
        response = self.client.post('/submit_section', data={
            'name': 'Alice',
            'team': 'Red',
            'date': 'January 15, 2025',
            'date_str': '2025-01-15',
            'section': '1.1',
        })

        self.assertEqual(response.status_code, 302)
        mock_insert.assert_called_once()

    @patch('routes.home.insert_completed_section')
    def test_submit_section_passes_correct_data(self, mock_insert):
        """POST /submit_section should pass correct data to insert"""
        self.client.post('/submit_section', data={
            'name': 'Alice',
            'team': 'Red',
            'date': 'January 15, 2025',
            'date_str': '2025-01-15',
            'section': '1.1',
        })

        call_args = mock_insert.call_args
        self.assertEqual(call_args[0][0]['Name'], 'Alice')
        self.assertEqual(call_args[0][0]['Team'], 'Red')
        self.assertEqual(call_args[0][0]['Section'], '1.1')

    @patch('routes.home.insert_completed_section')
    def test_submit_section_redirects_to_team_page(self, mock_insert):
        """POST /submit_section should redirect to team page"""
        response = self.client.post('/submit_section', data={
            'name': 'Alice',
            'team': 'Red',
            'date': 'January 15, 2025',
            'date_str': '2025-01-15',
            'section': '1.1',
        })

        self.assertEqual(response.status_code, 302)
        self.assertIn('/home/2025-01-15/team/Red', response.location)

    @patch('routes.home.insert_completed_section')
    def test_submit_section_handles_error(self, mock_insert):
        """POST /submit_section should redirect on error"""
        mock_insert.side_effect = Exception('Error')

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

    @patch('routes.home.update_completed_section')
    @patch('routes.home.get_schedule')
    def test_edit_section_calls_update_record(self, mock_get_schedule, mock_update):
        """POST /edit_section should call update"""
        mock_get_schedule.return_value = [{'Date': 'January 15, 2025', 'Theme': 'Test'}]

        response = self.client.post('/edit_section', data={
            'date_str': '2025-01-15',
            'team_name': 'Red',
            'kid_name': 'Alice',
            'section_name': '1.1',
            'Section Complete': 'on',
        })

        self.assertEqual(response.status_code, 302)
        mock_update.assert_called_once()

    @patch('routes.home.update_completed_section')
    @patch('routes.home.get_schedule')
    def test_edit_section_passes_correct_updates(self, mock_get_schedule, mock_update):
        """POST /edit_section should pass correct updates"""
        mock_get_schedule.return_value = [{'Date': 'January 15, 2025', 'Theme': 'Test'}]

        self.client.post('/edit_section', data={
            'date_str': '2025-01-15',
            'team_name': 'Red',
            'kid_name': 'Alice',
            'section_name': '1.1',
            'Section Complete': 'on',
            'Silver Credit': 'on',
        })

        call_args = mock_update.call_args
        updates = call_args[0][1]
        self.assertEqual(updates['Section Complete'], 'TRUE')
        self.assertEqual(updates['Silver Credit'], 'TRUE')
        self.assertEqual(updates['Gold Credit'], 'FALSE')


class TestHomeSectionDetailsRoutes(unittest.TestCase):
    """Tests for section details route"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('routes.home.get_completed_sections')
    @patch('routes.home.get_schedule')
    def test_section_details_shows_entry(self, mock_get_schedule, mock_get_sections):
        """GET section details should show section entry"""
        mock_get_schedule.return_value = [
            {'Date': 'January 15, 2025', 'Theme': 'Test'}
        ]
        mock_get_sections.return_value = [
            {'Date': 'January 15, 2025', 'Team': 'Red', 'Name': 'Alice', 'Section': '1.1'}
        ]

        response = self.client.get('/home/2025-01-15/team/Red/kid/Alice/section/1.1')

        self.assertEqual(response.status_code, 200)

    @patch('routes.home.get_completed_sections')
    @patch('routes.home.get_schedule')
    def test_section_details_handles_url_encoding(self, mock_get_schedule, mock_get_sections):
        """Should handle URL-encoded kid names"""
        mock_get_schedule.return_value = [
            {'Date': 'January 15, 2025', 'Theme': 'Test'}
        ]
        mock_get_sections.return_value = [
            {'Date': 'January 15, 2025', 'Team': 'Red', 'Name': "Alice O'Brien", 'Section': '1.1'}
        ]

        response = self.client.get("/home/2025-01-15/team/Red/kid/Alice%20O'Brien/section/1.1")

        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
