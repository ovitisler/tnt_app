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


class TestAttendanceRoutes(unittest.TestCase):
    """Tests for attendance route handlers"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('routes.attendance.get_attendance_schedule')
    def test_attendance_returns_schedule_data(self, mock_get_schedule):
        """GET /attendance should return attendance schedule data"""
        mock_get_schedule.return_value = [
            {'Date': 'January 15, 2025', 'Theme': 'Test Theme'}
        ]

        response = self.client.get('/attendance')

        self.assertEqual(response.status_code, 200)
        mock_get_schedule.assert_called_once()

    @patch('routes.attendance.get_attendance_schedule')
    def test_attendance_handles_error(self, mock_get_schedule):
        """GET /attendance should handle errors gracefully"""
        mock_get_schedule.side_effect = Exception('Sheet not found')

        response = self.client.get('/attendance')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sheet not found', response.data)


class TestAttendanceDetailsRoutes(unittest.TestCase):
    """Tests for attendance details route"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('routes.attendance.get_attendance_totals')
    @patch('routes.attendance.get_attendance_schedule')
    def test_attendance_details_shows_day_data(self, mock_get_schedule, mock_get_totals):
        """GET /attendance/<date_str> should show day details"""
        mock_get_schedule.return_value = [
            {'Date': 'January 15, 2025', 'Theme': 'Test Theme'}
        ]
        mock_get_totals.return_value = [
            {'Date': 'January 15, 2025', 'Team': 'Red', 'Present': 5}
        ]

        response = self.client.get('/attendance/2025-01-15')

        self.assertEqual(response.status_code, 200)

    @patch('routes.attendance.get_attendance_schedule')
    def test_attendance_details_redirects_if_date_not_found(self, mock_get_schedule):
        """GET /attendance/<date_str> should redirect if date not in schedule"""
        mock_get_schedule.return_value = [
            {'Date': 'January 15, 2025', 'Theme': 'Test Theme'}
        ]

        response = self.client.get('/attendance/2025-12-31')

        self.assertEqual(response.status_code, 302)

    @patch('routes.attendance.get_attendance_schedule')
    def test_attendance_details_handles_error(self, mock_get_schedule):
        """GET /attendance/<date_str> should redirect on error"""
        mock_get_schedule.side_effect = Exception('Error')

        response = self.client.get('/attendance/2025-01-15')

        self.assertEqual(response.status_code, 302)


class TestTeamAttendanceDetailsRoutes(unittest.TestCase):
    """Tests for team attendance details route"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('routes.attendance.get_attendance_entries')
    @patch('routes.attendance.get_attendance_totals')
    @patch('routes.attendance.get_attendance_schedule')
    def test_team_attendance_shows_team_data(self, mock_get_schedule, mock_get_totals, mock_get_entries):
        """GET /attendance/<date>/team/<team> should show team attendance"""
        mock_get_schedule.return_value = [
            {'Date': 'January 15, 2025', 'Theme': 'Test'}
        ]
        mock_get_totals.return_value = [
            {'Date': 'January 15, 2025', 'Team': 'Red', 'Present': 5}
        ]
        mock_get_entries.return_value = [
            {'Date': 'January 15, 2025', 'Team': 'Red', 'Name': 'Alice', 'Present': True}
        ]

        response = self.client.get('/attendance/2025-01-15/team/Red')

        self.assertEqual(response.status_code, 200)

    @patch('routes.attendance.get_attendance_schedule')
    def test_team_attendance_redirects_if_date_not_found(self, mock_get_schedule):
        """Should redirect if date not in schedule"""
        mock_get_schedule.return_value = []

        response = self.client.get('/attendance/2025-01-15/team/Red')

        self.assertEqual(response.status_code, 302)


class TestKidAttendanceDetailsRoutes(unittest.TestCase):
    """Tests for kid attendance details route"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('routes.attendance.get_attendance_entries')
    @patch('routes.attendance.get_attendance_schedule')
    def test_kid_attendance_shows_entry(self, mock_get_schedule, mock_get_entries):
        """GET /attendance/<date>/team/<team>/kid/<kid> should show kid entry"""
        mock_get_schedule.return_value = [
            {'Date': 'January 15, 2025', 'Theme': 'Test'}
        ]
        mock_get_entries.return_value = [
            {'Date': 'January 15, 2025', 'Team': 'Red', 'Name': 'Alice', 'Present': True}
        ]

        response = self.client.get('/attendance/2025-01-15/team/Red/kid/Alice')

        self.assertEqual(response.status_code, 200)

    @patch('routes.attendance.get_attendance_entries')
    @patch('routes.attendance.get_attendance_schedule')
    def test_kid_attendance_handles_url_encoding(self, mock_get_schedule, mock_get_entries):
        """Should handle URL-encoded kid names"""
        mock_get_schedule.return_value = [
            {'Date': 'January 15, 2025', 'Theme': 'Test'}
        ]
        mock_get_entries.return_value = [
            {'Date': 'January 15, 2025', 'Team': 'Red', 'Name': "Alice O'Brien", 'Present': True}
        ]

        response = self.client.get("/attendance/2025-01-15/team/Red/kid/Alice%20O'Brien")

        self.assertEqual(response.status_code, 200)


class TestCheckinFormRoutes(unittest.TestCase):
    """Tests for checkin form route"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('routes.attendance.get_roster')
    @patch('routes.attendance.get_attendance_schedule')
    def test_checkin_form_shows_team_kids(self, mock_get_schedule, mock_get_roster):
        """GET /attendance/<date>/team/<team>/checkin should show form with team kids"""
        mock_get_schedule.return_value = [
            {'Date': 'January 15, 2025', 'Theme': 'Test'}
        ]
        mock_get_roster.return_value = [
            {'Name': 'Alice', 'Group': 'Red'},
            {'Name': 'Bob', 'Group': 'Blue'}
        ]

        response = self.client.get('/attendance/2025-01-15/team/Red/checkin')

        self.assertEqual(response.status_code, 200)

    @patch('routes.attendance.get_attendance_schedule')
    def test_checkin_form_redirects_if_date_not_found(self, mock_get_schedule):
        """Should redirect if date not in schedule"""
        mock_get_schedule.return_value = []

        response = self.client.get('/attendance/2025-01-15/team/Red/checkin')

        self.assertEqual(response.status_code, 302)


class TestSubmitCheckinRoutes(unittest.TestCase):
    """Tests for submit checkin POST route"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('routes.attendance.insert_attendance_entry')
    def test_submit_checkin_inserts_record(self, mock_insert):
        """POST /submit_checkin should insert a record"""
        response = self.client.post('/submit_checkin', data={
            'name': 'Alice',
            'team': 'Red',
            'date': 'January 15, 2025',
            'date_str': '2025-01-15',
            'present': 'on',
        })

        self.assertEqual(response.status_code, 302)
        mock_insert.assert_called_once()

    @patch('routes.attendance.insert_attendance_entry')
    def test_submit_checkin_passes_correct_data(self, mock_insert):
        """POST /submit_checkin should pass correct data to insert"""
        self.client.post('/submit_checkin', data={
            'name': 'Alice',
            'team': 'Red',
            'date': 'January 15, 2025',
            'date_str': '2025-01-15',
            'present': 'on',
        })

        call_args = mock_insert.call_args
        self.assertEqual(call_args[0][0]['Name'], 'Alice')
        self.assertEqual(call_args[0][0]['Team'], 'Red')

    @patch('routes.attendance.insert_attendance_entry')
    def test_submit_checkin_redirects_to_team_page(self, mock_insert):
        """POST /submit_checkin should redirect to team attendance page"""
        response = self.client.post('/submit_checkin', data={
            'name': 'Alice',
            'team': 'Red',
            'date': 'January 15, 2025',
            'date_str': '2025-01-15',
        })

        self.assertEqual(response.status_code, 302)
        self.assertIn('/attendance/2025-01-15/team/Red', response.location)

    @patch('routes.attendance.insert_attendance_entry')
    def test_submit_checkin_handles_error(self, mock_insert):
        """POST /submit_checkin should redirect on error"""
        mock_insert.side_effect = Exception('Error')

        response = self.client.post('/submit_checkin', data={
            'name': 'Alice',
            'team': 'Red',
            'date': 'January 15, 2025',
            'date_str': '2025-01-15',
        })

        self.assertEqual(response.status_code, 302)


class TestEditAttendanceRoutes(unittest.TestCase):
    """Tests for edit attendance POST route"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_edit_attendance_get_redirects(self):
        """GET /edit_attendance should redirect"""
        response = self.client.get('/edit_attendance')

        self.assertEqual(response.status_code, 302)

    @patch('routes.attendance.update_attendance_entry')
    @patch('routes.attendance.get_attendance_schedule')
    def test_edit_attendance_calls_update_record(self, mock_get_schedule, mock_update):
        """POST /edit_attendance should call update"""
        mock_get_schedule.return_value = [{'Date': 'January 15, 2025', 'Theme': 'Test'}]

        response = self.client.post('/edit_attendance', data={
            'date_str': '2025-01-15',
            'team_name': 'Red',
            'kid_name': 'Alice',
            'Present': 'on',
        })

        self.assertEqual(response.status_code, 302)
        mock_update.assert_called_once()

    @patch('routes.attendance.update_attendance_entry')
    @patch('routes.attendance.get_attendance_schedule')
    def test_edit_attendance_passes_correct_updates(self, mock_get_schedule, mock_update):
        """POST /edit_attendance should pass correct updates"""
        mock_get_schedule.return_value = [{'Date': 'January 15, 2025', 'Theme': 'Test'}]

        self.client.post('/edit_attendance', data={
            'date_str': '2025-01-15',
            'team_name': 'Red',
            'kid_name': 'Alice',
            'Present': 'on',
            'Has Bible': 'on',
        })

        call_args = mock_update.call_args
        updates = call_args[0][1]
        self.assertEqual(updates['Present'], 'TRUE')
        self.assertEqual(updates['Has Bible'], 'TRUE')


if __name__ == '__main__':
    unittest.main()
