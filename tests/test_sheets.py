import sys
import time
import unittest
from unittest.mock import patch, MagicMock

# Mock gspread and oauth2client before importing sheets module
sys.modules['gspread'] = MagicMock()
sys.modules['gspread.exceptions'] = MagicMock()
sys.modules['oauth2client'] = MagicMock()
sys.modules['oauth2client.service_account'] = MagicMock()

with patch.dict('os.environ', {'GOOGLE_SHEETS_CREDS': '{}'}):
    from models import sheets
    from models.cache import CacheEntry


class TestCacheEntry(unittest.TestCase):
    """Tests for CacheEntry dataclass"""

    def test_age_calculation(self):
        """Should calculate age correctly"""
        entry = CacheEntry(data=[], timestamp=time.time() - 100, size_bytes=0)
        self.assertAlmostEqual(entry.age(), 100, delta=1)

    def test_is_stale(self):
        """Should return True when age exceeds TTL"""
        entry = CacheEntry(data=[], timestamp=time.time() - 100, size_bytes=0)
        self.assertTrue(entry.is_stale(ttl=50))
        self.assertFalse(entry.is_stale(ttl=200))

    def test_is_fresh(self):
        """Should return True when age is within TTL"""
        entry = CacheEntry(data=[], timestamp=time.time() - 10, size_bytes=0)
        self.assertTrue(entry.is_fresh(ttl=50))
        self.assertFalse(entry.is_fresh(ttl=5))

    def test_mark_fresh(self):
        """Should update timestamp to current time"""
        entry = CacheEntry(data=[], timestamp=time.time() - 100, size_bytes=0)
        old_timestamp = entry.timestamp
        entry.mark_fresh()
        self.assertGreater(entry.timestamp, old_timestamp)

    def test_add_row(self):
        """Should append row and update size"""
        entry = CacheEntry(data=[{'Name': 'Existing'}], timestamp=time.time() - 100, size_bytes=100)
        old_timestamp = entry.timestamp
        
        entry.add_row({'Name': 'New'})
        
        self.assertEqual(len(entry.data), 2)
        self.assertEqual(entry.data[-1], {'Name': 'New'})
        self.assertGreater(entry.size_bytes, 100)
        self.assertGreater(entry.timestamp, old_timestamp)


class TestGetTtlForSheet(unittest.TestCase):
    """Tests for _get_ttl_for_sheet()"""

    def test_static_sheets_get_long_ttl(self):
        """Static sheets should get 1 day TTL"""
        for sheet in sheets.STATIC_SHEETS:
            with self.subTest(sheet=sheet):
                ttl = sheets._get_ttl_for_sheet(sheet)
                self.assertEqual(ttl, sheets.CACHE_TTL_STATIC)

    def test_dynamic_sheets_get_short_ttl(self):
        """Dynamic sheets should get short TTL"""
        dynamic_sheets = [
            sheets.COMPLETED_SECTIONS_SHEET,
            sheets.ATTENDANCE_ENTRIES_SHEET,
            sheets.WEEKLY_TOTALS_SHEET,
        ]
        for sheet in dynamic_sheets:
            with self.subTest(sheet=sheet):
                ttl = sheets._get_ttl_for_sheet(sheet)
                self.assertEqual(ttl, sheets.CACHE_TTL_DYNAMIC)

    def test_unknown_sheets_get_dynamic_ttl(self):
        """Unknown sheets should default to dynamic TTL"""
        ttl = sheets._get_ttl_for_sheet('Unknown Sheet')
        self.assertEqual(ttl, sheets.CACHE_TTL_DYNAMIC)


class TestCacheAppendRow(unittest.TestCase):
    """Tests for cache_append_row()"""

    def setUp(self):
        """Clear cache before each test"""
        sheets._cache.clear()

    def tearDown(self):
        """Clear cache after each test"""
        sheets._cache.clear()

    def test_appends_to_existing_cache(self):
        """Should append row to existing cache"""
        sheets._cache.set('Test Sheet', [{'Name': 'Existing'}], 100)

        sheets.cache_append_row('Test Sheet', {'Name': 'New Row'})

        cached = sheets._cache.get('Test Sheet')
        self.assertEqual(len(cached.data), 2)
        self.assertEqual(cached.data[-1], {'Name': 'New Row'})

    def test_updates_timestamp(self):
        """Should update cache timestamp to mark as fresh"""
        sheets._cache.set('Test Sheet', [], 0)
        cached = sheets._cache.get('Test Sheet')
        cached.timestamp = time.time() - 100
        old_time = cached.timestamp

        sheets.cache_append_row('Test Sheet', {'Name': 'New'})

        self.assertGreater(sheets._cache.get('Test Sheet').timestamp, old_time)

    def test_updates_size_bytes(self):
        """Should update size_bytes estimate"""
        sheets._cache.set('Test Sheet', [], 100)

        sheets.cache_append_row('Test Sheet', {'Name': 'New'})

        self.assertGreater(sheets._cache.get('Test Sheet').size_bytes, 100)

    def test_no_cache_does_nothing(self):
        """Should do nothing if cache doesn't exist"""
        sheets.cache_append_row('Nonexistent Sheet', {'Name': 'New'})
        self.assertFalse(sheets._cache.has('Nonexistent Sheet'))


class TestCacheUpdateRow(unittest.TestCase):
    """Tests for cache_update_row()"""

    def setUp(self):
        """Clear cache before each test"""
        sheets._cache.clear()

    def tearDown(self):
        """Clear cache after each test"""
        sheets._cache.clear()

    def test_updates_matching_row(self):
        """Should update row that matches the predicate"""
        sheets._cache.set('Test Sheet', [
            {'Name': 'Alice', 'Score': 10},
            {'Name': 'Bob', 'Score': 20},
        ], 100)

        result = sheets.cache_update_row(
            'Test Sheet',
            lambda row: row['Name'] == 'Bob',
            {'Score': 25}
        )

        self.assertTrue(result)
        self.assertEqual(sheets._cache.get('Test Sheet').data[1]['Score'], 25)

    def test_updates_timestamp(self):
        """Should update timestamp when row is found"""
        sheets._cache.set('Test Sheet', [{'Name': 'Alice'}], 100)
        cached = sheets._cache.get('Test Sheet')
        cached.timestamp = time.time() - 100
        old_time = cached.timestamp

        sheets.cache_update_row(
            'Test Sheet',
            lambda row: row['Name'] == 'Alice',
            {'Score': 10}
        )

        self.assertGreater(sheets._cache.get('Test Sheet').timestamp, old_time)

    def test_no_match_returns_false(self):
        """Should return False if no row matches"""
        sheets._cache.set('Test Sheet', [{'Name': 'Alice'}], 100)

        result = sheets.cache_update_row(
            'Test Sheet',
            lambda row: row['Name'] == 'Bob',
            {'Score': 10}
        )

        self.assertFalse(result)

    def test_no_cache_returns_false(self):
        """Should return False if cache doesn't exist"""
        result = sheets.cache_update_row(
            'Nonexistent Sheet',
            lambda row: True,
            {'Score': 10}
        )
        self.assertFalse(result)


class TestRefreshComputedSheets(unittest.TestCase):
    """Tests for refresh_computed_sheets()"""

    def setUp(self):
        sheets._cache.clear()
        sheets._pending_refreshes.clear()

    def tearDown(self):
        sheets._cache.clear()
        sheets._pending_refreshes.clear()

    @patch.object(sheets, '_trigger_background_refresh')
    def test_triggers_refresh_for_related_sheets(self, mock_refresh):
        """Should trigger refresh for related computed sheets"""
        sheets.refresh_computed_sheets(sheets.COMPLETED_SECTIONS_SHEET)

        # Should refresh Weekly Totals but not the RAW sheet itself
        mock_refresh.assert_called_once_with(sheets.WEEKLY_TOTALS_SHEET)

    @patch.object(sheets, '_trigger_background_refresh')
    def test_no_refresh_for_unknown_sheet(self, mock_refresh):
        """Should not trigger refresh for sheets not in INVALIDATION_MAP"""
        sheets.refresh_computed_sheets('Unknown Sheet')

        mock_refresh.assert_not_called()


class TestInvalidationMap(unittest.TestCase):
    """Tests for INVALIDATION_MAP configuration"""

    def test_completed_sections_triggers_weekly_totals(self):
        """Writing to Completed Sections RAW should refresh Weekly Totals"""
        related = sheets.INVALIDATION_MAP.get(sheets.COMPLETED_SECTIONS_SHEET, [])
        self.assertIn(sheets.WEEKLY_TOTALS_SHEET, related)

    def test_attendance_entries_triggers_attendance_totals(self):
        """Writing to Attendance Entries RAW should refresh Attendance Totals"""
        related = sheets.INVALIDATION_MAP.get(sheets.ATTENDANCE_ENTRIES_SHEET, [])
        self.assertIn(sheets.WEEKLY_ATTENDANCE_TOTALS_SHEET, related)


if __name__ == '__main__':
    unittest.main()
