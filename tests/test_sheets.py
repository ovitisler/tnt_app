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
