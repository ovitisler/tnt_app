import unittest
from models.utils import parse_date_string, dates_match, date_to_url, url_to_date


class TestParseDateString(unittest.TestCase):
    """Tests for parse_date_string()"""

    def test_iso_format(self):
        """Should parse ISO format dates"""
        result = parse_date_string('2025-09-17T00:00:00.000Z')
        self.assertEqual(result.year, 2025)
        self.assertEqual(result.month, 9)
        self.assertEqual(result.day, 17)

    def test_readable_format(self):
        """Should parse 'Month Day, Year' format"""
        result = parse_date_string('September 17, 2025')
        self.assertEqual(result.year, 2025)
        self.assertEqual(result.month, 9)
        self.assertEqual(result.day, 17)

    def test_different_months(self):
        """Should handle all months correctly"""
        test_cases = [
            ('January 1, 2025', 1, 1),
            ('February 14, 2025', 2, 14),
            ('March 15, 2025', 3, 15),
            ('December 31, 2025', 12, 31),
        ]
        for date_str, expected_month, expected_day in test_cases:
            with self.subTest(date_str=date_str):
                result = parse_date_string(date_str)
                self.assertEqual(result.month, expected_month)
                self.assertEqual(result.day, expected_day)


class TestDatesMatch(unittest.TestCase):
    """Tests for dates_match()"""

    def test_same_format_match(self):
        """Same format dates should match"""
        self.assertTrue(dates_match('September 17, 2025', 'September 17, 2025'))

    def test_different_formats_match(self):
        """Different format dates representing same day should match"""
        self.assertTrue(dates_match('September 17, 2025', '2025-09-17T00:00:00.000Z'))
        self.assertTrue(dates_match('2025-09-17T00:00:00.000Z', 'September 17, 2025'))

    def test_different_dates_no_match(self):
        """Different dates should not match"""
        self.assertFalse(dates_match('September 17, 2025', 'September 18, 2025'))
        self.assertFalse(dates_match('September 17, 2025', 'October 17, 2025'))

    def test_empty_values(self):
        """Empty or None values should not match"""
        self.assertFalse(dates_match('', 'September 17, 2025'))
        self.assertFalse(dates_match('September 17, 2025', ''))
        self.assertFalse(dates_match(None, 'September 17, 2025'))
        self.assertFalse(dates_match('September 17, 2025', None))
        self.assertFalse(dates_match('', ''))
        self.assertFalse(dates_match(None, None))

    def test_fallback_string_comparison(self):
        """Invalid dates should fall back to string comparison"""
        self.assertTrue(dates_match('invalid', 'invalid'))
        self.assertFalse(dates_match('invalid1', 'invalid2'))


class TestDateToUrl(unittest.TestCase):
    """Tests for date_to_url()"""

    def test_readable_to_url(self):
        """Should convert readable format to YYYY-MM-DD"""
        self.assertEqual(date_to_url('September 17, 2025'), '2025-09-17')

    def test_iso_to_url(self):
        """Should convert ISO format to YYYY-MM-DD"""
        self.assertEqual(date_to_url('2025-09-17T00:00:00.000Z'), '2025-09-17')

    def test_already_url_format(self):
        """Should handle already-URL-formatted dates"""
        self.assertEqual(date_to_url('2025-09-17'), '2025-09-17')

    def test_unparseable_returns_original(self):
        """Should return original string if can't parse"""
        self.assertEqual(date_to_url('unparseable'), 'unparseable')


class TestUrlToDate(unittest.TestCase):
    """Tests for url_to_date()"""

    def test_url_to_readable(self):
        """Should convert YYYY-MM-DD to readable format"""
        self.assertEqual(url_to_date('2025-09-17'), 'September 17, 2025')

    def test_single_digit_day(self):
        """Should handle single digit days without leading zero in output"""
        self.assertEqual(url_to_date('2025-09-01'), 'September 01, 2025')

    def test_unparseable_returns_original(self):
        """Should return original string if can't parse"""
        self.assertEqual(url_to_date('unparseable'), 'unparseable')


class TestRoundTrip(unittest.TestCase):
    """Tests for round-trip conversions"""

    def test_readable_round_trip(self):
        """Converting readable -> URL -> readable should preserve date"""
        original = 'September 17, 2025'
        url_format = date_to_url(original)
        back = url_to_date(url_format)
        self.assertTrue(dates_match(original, back))

    def test_url_round_trip(self):
        """Converting URL -> readable -> URL should preserve date"""
        original = '2025-09-17'
        readable = url_to_date(original)
        back = date_to_url(readable)
        self.assertEqual(original, back)


if __name__ == '__main__':
    unittest.main()
