import unittest
import models.metrics as metrics_module


class TestLogApiCall(unittest.TestCase):
    """Tests for log_api_call()"""

    def setUp(self):
        metrics_module.reset_metrics()

    def tearDown(self):
        metrics_module.reset_metrics()

    def test_cache_hit_increments_counter(self):
        """Cache hit should increment cache_hits"""
        metrics_module.log_api_call('read', 'Test Sheet', source='cache')
        self.assertEqual(metrics_module._metrics['cache_hits'], 1)
        self.assertEqual(metrics_module._metrics['cache_misses'], 0)

    def test_cache_stale_increments_stale_counter(self):
        """Stale cache hit should increment cache_hits_stale"""
        metrics_module.log_api_call('read', 'Test Sheet', source='cache-stale')
        self.assertEqual(metrics_module._metrics['cache_hits_stale'], 1)

    def test_google_read_increments_miss_and_reads(self):
        """Google read should increment cache_misses and total_reads"""
        metrics_module.log_api_call('read', 'Test Sheet', size_bytes=1000, source='google')
        self.assertEqual(metrics_module._metrics['cache_misses'], 1)
        self.assertEqual(metrics_module._metrics['total_reads'], 1)
        self.assertEqual(metrics_module._metrics['total_bytes'], 1000)

    def test_google_bg_increments_background_refreshes(self):
        """Background refresh should increment background_refreshes"""
        metrics_module.log_api_call('read', 'Test Sheet', size_bytes=500, source='google-bg')
        self.assertEqual(metrics_module._metrics['background_refreshes'], 1)
        self.assertEqual(metrics_module._metrics['total_reads'], 1)
        self.assertEqual(metrics_module._metrics['total_bytes'], 500)

    def test_write_increments_total_writes(self):
        """Write operation should increment total_writes"""
        metrics_module.log_api_call('write', 'Test Sheet', source='google')
        self.assertEqual(metrics_module._metrics['total_writes'], 1)

    def test_recent_calls_tracked(self):
        """Should track recent calls"""
        metrics_module.log_api_call('read', 'Test Sheet', source='cache')
        self.assertEqual(len(metrics_module._metrics['recent_calls']), 1)
        self.assertEqual(metrics_module._metrics['recent_calls'][0]['sheet'], 'Test Sheet')


class TestLogRateLimitError(unittest.TestCase):
    """Tests for log_rate_limit_error()"""

    def setUp(self):
        metrics_module.reset_metrics()

    def tearDown(self):
        metrics_module.reset_metrics()

    def test_increments_error_counter(self):
        """Should increment rate_limit_errors"""
        metrics_module.log_rate_limit_error('Test Sheet')
        self.assertEqual(metrics_module._metrics['rate_limit_errors'], 1)

    def test_simulated_also_increments(self):
        """Simulated errors should also increment counter"""
        metrics_module.log_rate_limit_error('Test Sheet', simulated=True)
        self.assertEqual(metrics_module._metrics['rate_limit_errors'], 1)


class TestResetMetrics(unittest.TestCase):
    """Tests for reset_metrics()"""

    def test_resets_all_counters(self):
        """Should reset all counters to zero"""
        # Add some data
        metrics_module.log_api_call('read', 'Test', source='cache')
        metrics_module.log_api_call('read', 'Test', source='cache-stale')
        metrics_module.log_api_call('read', 'Test', source='google')
        metrics_module.log_api_call('read', 'Test', source='google-bg')
        metrics_module.log_rate_limit_error('Test')

        metrics_module.reset_metrics()

        self.assertEqual(metrics_module._metrics['cache_hits'], 0)
        self.assertEqual(metrics_module._metrics['cache_hits_stale'], 0)
        self.assertEqual(metrics_module._metrics['cache_misses'], 0)
        self.assertEqual(metrics_module._metrics['background_refreshes'], 0)
        self.assertEqual(metrics_module._metrics['total_reads'], 0)
        self.assertEqual(metrics_module._metrics['total_writes'], 0)
        self.assertEqual(metrics_module._metrics['total_bytes'], 0)
        self.assertEqual(metrics_module._metrics['rate_limit_errors'], 0)
        self.assertEqual(len(metrics_module._metrics['recent_calls']), 0)


class TestGetMetrics(unittest.TestCase):
    """Tests for get_metrics()"""

    def setUp(self):
        metrics_module.reset_metrics()

    def tearDown(self):
        metrics_module.reset_metrics()

    def test_returns_all_fields(self):
        """Should return all expected fields"""
        metrics = metrics_module.get_metrics()

        expected_fields = [
            'total_google_reads', 'total_writes', 'total_bytes',
            'cache_hits', 'cache_hits_stale', 'cache_misses',
            'background_refreshes', 'cache_hit_rate', 'rate_limit_errors',
        ]
        for field in expected_fields:
            with self.subTest(field=field):
                self.assertIn(field, metrics)

    def test_cache_hit_rate_calculation(self):
        """Should calculate cache hit rate correctly"""
        metrics_module.log_api_call('read', 'Test', source='cache')
        metrics_module.log_api_call('read', 'Test', source='cache')
        metrics_module.log_api_call('read', 'Test', source='google')

        metrics = metrics_module.get_metrics()

        # 2 hits out of 3 total = 66.7%
        self.assertEqual(metrics['cache_hit_rate'], '66.7%')


if __name__ == '__main__':
    unittest.main()
