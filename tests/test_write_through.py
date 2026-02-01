import unittest
from unittest.mock import patch, MagicMock


class TestInsertRecordWriteThrough(unittest.TestCase):
    """Tests for insert_record write-through caching flow"""

    def setUp(self):
        self.mock_worksheet = MagicMock()
        self.mock_worksheet.row_values.return_value = ['timestamp', 'Name', 'Team', 'Date', 'Section']

        self.mock_cache = MagicMock()

        self.patches = [
            patch('models.data.get_worksheet', return_value=self.mock_worksheet),
            patch('models.data._cache', self.mock_cache),
            patch('models.data._trigger_background_refresh'),
            patch('models.data.INVALIDATION_MAP', {'Completed Sections RAW': ['Completed Sections']}),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_insert_record_writes_to_storage(self):
        """insert_record should write to storage first"""
        from models.data import insert_record

        insert_record('Completed Sections RAW', {
            'Name': 'Test Kid',
            'Team': 'Red',
        })

        self.mock_worksheet.append_row.assert_called_once()

    def test_insert_record_updates_cache(self):
        """insert_record should update cache after writing"""
        from models.data import insert_record

        insert_record('Completed Sections RAW', {
            'Name': 'Test Kid',
            'Team': 'Red',
        })

        self.mock_cache.append_row.assert_called_once()
        call_args = self.mock_cache.append_row.call_args
        self.assertEqual(call_args[0][0], 'Completed Sections RAW')
        self.assertEqual(call_args[0][1]['Name'], 'Test Kid')
        self.assertEqual(call_args[0][1]['Team'], 'Red')

    def test_insert_record_refreshes_related_tables(self):
        """insert_record should trigger refresh for related tables"""
        from models.data import insert_record, _trigger_background_refresh

        insert_record('Completed Sections RAW', {
            'Name': 'Test Kid',
            'Team': 'Red',
        })

        _trigger_background_refresh.assert_called_once_with('Completed Sections')

    def test_insert_record_correct_order(self):
        """insert_record should write storage -> cache -> refresh in order"""
        from models.data import insert_record, _trigger_background_refresh

        call_order = []

        self.mock_worksheet.append_row.side_effect = lambda *a, **k: call_order.append('storage')
        self.mock_cache.append_row.side_effect = lambda *a, **k: call_order.append('cache')
        _trigger_background_refresh.side_effect = lambda *a: call_order.append('refresh')

        insert_record('Completed Sections RAW', {
            'Name': 'Test Kid',
            'Team': 'Red',
        })

        self.assertEqual(call_order, ['storage', 'cache', 'refresh'])

    def test_insert_record_adds_timestamp(self):
        """insert_record should add timestamp if not present"""
        from models.data import insert_record

        result = insert_record('Completed Sections RAW', {
            'Name': 'Test Kid',
        })

        self.assertIn('timestamp', result)


class TestUpdateRecordWriteThrough(unittest.TestCase):
    """Tests for update_record write-through caching flow"""

    def setUp(self):
        self.mock_worksheet = MagicMock()
        self.mock_worksheet.row_values.return_value = ['Name', 'Team', 'Silver Credit']
        self.mock_worksheet.get_all_records.return_value = [
            {'Name': 'Test Kid', 'Team': 'Red', 'Silver Credit': 'FALSE'}
        ]

        self.mock_cache = MagicMock()

        self.patches = [
            patch('models.data.get_worksheet', return_value=self.mock_worksheet),
            patch('models.data._cache', self.mock_cache),
            patch('models.data._trigger_background_refresh'),
            patch('models.data.INVALIDATION_MAP', {'Completed Sections RAW': ['Completed Sections']}),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_update_record_updates_storage(self):
        """update_record should update storage first"""
        from models.data import update_record

        update_record(
            'Completed Sections RAW',
            lambda r: r.get('Name') == 'Test Kid',
            {'Silver Credit': 'TRUE'}
        )

        self.mock_worksheet.update_cell.assert_called()

    def test_update_record_updates_cache(self):
        """update_record should update cache after storage"""
        from models.data import update_record

        match_fn = lambda r: r.get('Name') == 'Test Kid'
        update_record('Completed Sections RAW', match_fn, {'Silver Credit': 'TRUE'})

        self.mock_cache.update_row.assert_called_once()

    def test_update_record_refreshes_related_tables(self):
        """update_record should trigger refresh for related tables"""
        from models.data import update_record, _trigger_background_refresh

        update_record(
            'Completed Sections RAW',
            lambda r: r.get('Name') == 'Test Kid',
            {'Silver Credit': 'TRUE'}
        )

        _trigger_background_refresh.assert_called_once_with('Completed Sections')

    def test_update_record_returns_true_on_match(self):
        """update_record should return True when a record is updated"""
        from models.data import update_record

        result = update_record(
            'Completed Sections RAW',
            lambda r: r.get('Name') == 'Test Kid',
            {'Silver Credit': 'TRUE'}
        )

        self.assertTrue(result)

    def test_update_record_returns_false_on_no_match(self):
        """update_record should return False when no record matches"""
        from models.data import update_record

        result = update_record(
            'Completed Sections RAW',
            lambda r: r.get('Name') == 'Nonexistent',
            {'Silver Credit': 'TRUE'}
        )

        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
