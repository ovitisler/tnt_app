import unittest
from unittest.mock import patch, MagicMock


class TestInsertWriteThrough(unittest.TestCase):
    """Tests for insert write-through caching flow"""

    def setUp(self):
        self.mock_worksheet = MagicMock()
        self.mock_worksheet.row_values.return_value = ['timestamp', 'Name', 'Team', 'Date', 'Section']

        self.mock_cache = MagicMock()

        self.patches = [
            patch('models.data._get_worksheet', return_value=self.mock_worksheet),
            patch('models.data._cache', self.mock_cache),
            patch('models.data._trigger_background_refresh'),
            patch('models.data.INVALIDATION_MAP', {'Completed Sections RAW': ['Completed Sections']}),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_insert_writes_to_storage(self):
        """insert should write to storage first"""
        from models.data import insert_completed_section

        insert_completed_section({
            'Name': 'Test Kid',
            'Team': 'Red',
        })

        self.mock_worksheet.append_row.assert_called_once()

    def test_insert_updates_cache(self):
        """insert should update cache after writing"""
        from models.data import insert_completed_section

        insert_completed_section({
            'Name': 'Test Kid',
            'Team': 'Red',
        })

        self.mock_cache.append_row.assert_called_once()
        call_args = self.mock_cache.append_row.call_args
        self.assertEqual(call_args[0][0], 'Completed Sections RAW')
        self.assertEqual(call_args[0][1]['Name'], 'Test Kid')
        self.assertEqual(call_args[0][1]['Team'], 'Red')

    def test_insert_refreshes_related_tables(self):
        """insert should trigger refresh for related tables"""
        from models.data import insert_completed_section, _trigger_background_refresh

        insert_completed_section({
            'Name': 'Test Kid',
            'Team': 'Red',
        })

        _trigger_background_refresh.assert_called_once_with('Completed Sections')

    def test_insert_cache_first(self):
        """insert should update cache first (sync), storage happens async"""
        from models.data import insert_completed_section
        import time

        call_order = []

        self.mock_worksheet.append_row.side_effect = lambda *a, **k: call_order.append('storage')
        self.mock_cache.append_row.side_effect = lambda *a, **k: call_order.append('cache')

        insert_completed_section({
            'Name': 'Test Kid',
            'Team': 'Red',
        })

        # Cache should be first
        self.assertEqual(call_order[0], 'cache')

        # Storage happens async - wait for background thread
        time.sleep(0.1)
        self.assertIn('storage', call_order)

    def test_insert_adds_timestamp(self):
        """insert should add timestamp if not present"""
        from models.data import insert_completed_section

        result = insert_completed_section({
            'Name': 'Test Kid',
        })

        self.assertIn('timestamp', result)


class TestUpdateWriteThrough(unittest.TestCase):
    """Tests for update write-through caching flow"""

    def setUp(self):
        self.mock_worksheet = MagicMock()
        self.mock_worksheet.row_values.return_value = ['Name', 'Team', 'Silver Credit']
        self.mock_worksheet.get_all_records.return_value = [
            {'Name': 'Test Kid', 'Team': 'Red', 'Silver Credit': 'FALSE'}
        ]

        self.mock_cache = MagicMock()
        mock_cached = MagicMock()
        mock_cached.data = [{'Name': 'Test Kid', 'Team': 'Red', 'Silver Credit': 'FALSE'}]
        self.mock_cache.get.return_value = mock_cached
        self.mock_cache.update_row.return_value = True

        self.patches = [
            patch('models.data._get_worksheet', return_value=self.mock_worksheet),
            patch('models.data._cache', self.mock_cache),
            patch('models.data._trigger_background_refresh'),
            patch('models.data.INVALIDATION_MAP', {'Completed Sections RAW': ['Completed Sections']}),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_update_updates_storage(self):
        """update should update storage first"""
        from models.data import update_completed_section

        update_completed_section(
            lambda r: r.get('Name') == 'Test Kid',
            {'Silver Credit': 'TRUE'}
        )

        self.mock_worksheet.update_cell.assert_called()

    def test_update_updates_cache(self):
        """update should update cache after storage"""
        from models.data import update_completed_section

        match_fn = lambda r: r.get('Name') == 'Test Kid'
        update_completed_section(match_fn, {'Silver Credit': 'TRUE'})

        self.mock_cache.update_row.assert_called_once()

    def test_update_refreshes_related_tables(self):
        """update should trigger refresh for related tables"""
        from models.data import update_completed_section, _trigger_background_refresh

        update_completed_section(
            lambda r: r.get('Name') == 'Test Kid',
            {'Silver Credit': 'TRUE'}
        )

        _trigger_background_refresh.assert_called_once_with('Completed Sections')

    def test_update_returns_true_on_match(self):
        """update should return True when a record is updated"""
        from models.data import update_completed_section

        result = update_completed_section(
            lambda r: r.get('Name') == 'Test Kid',
            {'Silver Credit': 'TRUE'}
        )

        self.assertTrue(result)

    def test_update_returns_false_on_no_match(self):
        """update should return False when no record matches in cache"""
        from models.data import update_completed_section

        self.mock_cache.update_row.return_value = False

        result = update_completed_section(
            lambda r: r.get('Name') == 'Nonexistent',
            {'Silver Credit': 'TRUE'}
        )

        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
