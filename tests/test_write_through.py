import unittest
from unittest.mock import patch, MagicMock
from flask import Flask


class TestWriteThroughFlow(unittest.TestCase):
    """Integration tests for write-through caching flow"""

    def setUp(self):
        """Set up Flask test client with mocked Google Sheets"""
        # Create patches for Google Sheets
        self.mock_get_worksheet = patch('routes.home.get_worksheet').start()
        self.mock_cache_append = patch('routes.home.cache_append_row').start()
        self.mock_refresh_computed = patch('routes.home.refresh_computed_sheets').start()
        self.mock_get_sheet_data = patch('routes.home.get_sheet_data').start()

        # Configure mocks
        mock_worksheet = MagicMock()
        mock_worksheet.row_values.return_value = ['timestamp', 'Name', 'Team', 'Date', 'Section', 'Section Complete', 'Silver Credit', 'Gold Credit']
        self.mock_get_worksheet.return_value = mock_worksheet

        self.mock_get_sheet_data.return_value = [
            {'Date': 'September 17, 2025', 'Theme': 'Test Theme'}
        ]

        # Create Flask app with routes
        from tnt import app
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def tearDown(self):
        patch.stopall()

    def test_submit_section_calls_cache_append(self):
        """submit_section should call cache_append_row after writing"""
        response = self.client.post('/submit_section', data={
            'name': 'Test Kid',
            'team': 'Red',
            'date': 'September 17, 2025',
            'date_str': '2025-09-17',
            'section': '1.1',
        })

        # Should redirect after success
        self.assertEqual(response.status_code, 302)

        # Should have called cache_append_row
        self.mock_cache_append.assert_called_once()
        call_args = self.mock_cache_append.call_args
        self.assertEqual(call_args[0][0], 'Completed Sections RAW')  # sheet name
        self.assertEqual(call_args[0][1]['Name'], 'Test Kid')
        self.assertEqual(call_args[0][1]['Team'], 'Red')
        self.assertEqual(call_args[0][1]['Section'], '1.1')

    def test_submit_section_calls_refresh_computed(self):
        """submit_section should call refresh_computed_sheets after writing"""
        self.client.post('/submit_section', data={
            'name': 'Test Kid',
            'team': 'Red',
            'date': 'September 17, 2025',
            'date_str': '2025-09-17',
            'section': '1.1',
        })

        # Should have called refresh_computed_sheets
        self.mock_refresh_computed.assert_called_once_with('Completed Sections RAW')

    def test_submit_section_writes_to_google_first(self):
        """submit_section should write to Google Sheets before updating cache"""
        call_order = []

        def track_worksheet(*args, **kwargs):
            call_order.append('get_worksheet')
            mock_ws = MagicMock()
            mock_ws.row_values.return_value = ['timestamp', 'Name', 'Team', 'Date', 'Section']
            mock_ws.append_row = lambda *a, **kw: call_order.append('append_row')
            return mock_ws

        def track_cache_append(*args, **kwargs):
            call_order.append('cache_append')

        def track_refresh(*args, **kwargs):
            call_order.append('refresh_computed')

        self.mock_get_worksheet.side_effect = track_worksheet
        self.mock_cache_append.side_effect = track_cache_append
        self.mock_refresh_computed.side_effect = track_refresh

        self.client.post('/submit_section', data={
            'name': 'Test Kid',
            'team': 'Red',
            'date': 'September 17, 2025',
            'date_str': '2025-09-17',
            'section': '1.1',
        })

        # Verify order: get_worksheet -> append_row -> cache_append -> refresh_computed
        self.assertEqual(call_order, ['get_worksheet', 'append_row', 'cache_append', 'refresh_computed'])


class TestAttendanceWriteThroughFlow(unittest.TestCase):
    """Integration tests for attendance write-through caching flow"""

    def setUp(self):
        """Set up Flask test client with mocked Google Sheets"""
        self.mock_get_worksheet = patch('routes.attendance.get_worksheet').start()
        self.mock_cache_append = patch('routes.attendance.cache_append_row').start()
        self.mock_refresh_computed = patch('routes.attendance.refresh_computed_sheets').start()
        self.mock_get_sheet_data = patch('routes.attendance.get_sheet_data').start()

        # Configure mocks
        mock_worksheet = MagicMock()
        mock_worksheet.row_values.return_value = ['timestamp', 'Name', 'Team', 'Date', 'Present', 'Has Bible']
        self.mock_get_worksheet.return_value = mock_worksheet

        self.mock_get_sheet_data.return_value = [
            {'Date': 'September 17, 2025', 'Theme': 'Test Theme'}
        ]

        from tnt import app
        app.config['TESTING'] = True
        self.client = app.test_client()

    def tearDown(self):
        patch.stopall()

    def test_submit_checkin_calls_cache_append(self):
        """submit_checkin should call cache_append_row after writing"""
        response = self.client.post('/submit_checkin', data={
            'name': 'Test Kid',
            'team': 'Red',
            'date': 'September 17, 2025',
            'date_str': '2025-09-17',
            'present': 'on',
        })

        self.assertEqual(response.status_code, 302)
        self.mock_cache_append.assert_called_once()
        call_args = self.mock_cache_append.call_args
        self.assertEqual(call_args[0][0], 'Attendance Entries RAW')
        self.assertEqual(call_args[0][1]['Name'], 'Test Kid')

    def test_submit_checkin_calls_refresh_computed(self):
        """submit_checkin should call refresh_computed_sheets after writing"""
        self.client.post('/submit_checkin', data={
            'name': 'Test Kid',
            'team': 'Red',
            'date': 'September 17, 2025',
            'date_str': '2025-09-17',
        })

        self.mock_refresh_computed.assert_called_once_with('Attendance Entries RAW')


if __name__ == '__main__':
    unittest.main()
