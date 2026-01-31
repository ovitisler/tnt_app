#!/usr/bin/env python3
"""
Load test script for TNT Reading Teams Tracker

Simulates multiple volunteers browsing the app to test caching
and Google Sheets API rate limits.

Usage:
    python load_test.py                      # 10 users, 60 seconds, reads only
    python load_test.py --users 25           # 25 users
    python load_test.py --duration 120       # Run for 2 minutes
    python load_test.py --delay 0.5          # Faster clicking (500ms between actions)
    python load_test.py --include-writes     # Include real write operations to test sheet
    python load_test.py --write-ratio 0.3    # 30% of actions are writes (default: 0.2)
"""

import argparse
import random
import time
import threading
import requests
from collections import defaultdict
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5001"

# Realistic page weights (what volunteers actually do)
READ_PAGES = [
    ("/", 20),                                    # Home - frequent
    ("/home/2025-09-17", 15),                     # Day details - frequent
    ("/home/2025-09-17/team/Green", 10),          # Team details - moderate
    ("/home/2025-09-17/team/Blue", 10),
    ("/home/2025-09-17/team/Red", 10),
    ("/attendance", 15),                          # Attendance home - frequent
    ("/attendance/2025-09-17", 10),               # Attendance day
    ("/attendance/2025-09-17/team/Green", 5),     # Team attendance
    ("/progress", 10),                            # Progress list
    ("/progress/student/Test%20Student", 5),      # Student progress
]


class LoadTestStats:
    def __init__(self):
        self.lock = threading.Lock()
        self.requests_made = 0
        self.requests_succeeded = 0
        self.requests_failed = 0
        self.reads = 0
        self.writes = 0
        self.response_times = []
        self.errors = defaultdict(int)
        self.pages_hit = defaultdict(int)

    def record_request(self, url, success, response_time, error=None, is_write=False):
        with self.lock:
            self.requests_made += 1
            self.response_times.append(response_time)
            self.pages_hit[url] += 1
            if is_write:
                self.writes += 1
            else:
                self.reads += 1
            if success:
                self.requests_succeeded += 1
            else:
                self.requests_failed += 1
                if error:
                    self.errors[str(error)[:50]] += 1

    def get_summary(self):
        with self.lock:
            if not self.response_times:
                return {}
            return {
                'total_requests': self.requests_made,
                'succeeded': self.requests_succeeded,
                'failed': self.requests_failed,
                'reads': self.reads,
                'writes': self.writes,
                'avg_response_ms': sum(self.response_times) / len(self.response_times),
                'max_response_ms': max(self.response_times),
                'min_response_ms': min(self.response_times),
            }


def weighted_choice(choices):
    """Pick a random item based on weights"""
    total = sum(weight for _, weight in choices)
    r = random.uniform(0, total)
    cumulative = 0
    for item, weight in choices:
        cumulative += weight
        if r <= cumulative:
            return item
    return choices[-1][0]


def do_write(session, stats):
    """Perform a test write operation"""
    url = "/test/write"
    full_url = f"{BASE_URL}{url}"

    try:
        start = time.time()
        response = session.post(full_url, json={}, timeout=15)
        elapsed_ms = (time.time() - start) * 1000

        success = response.status_code == 200
        error = None if success else f"HTTP {response.status_code}"
        stats.record_request(url, success, elapsed_ms, error, is_write=True)

    except Exception as e:
        stats.record_request(url, False, 0, str(e), is_write=True)


def do_read(session, stats):
    """Perform a read operation"""
    url = weighted_choice(READ_PAGES)
    full_url = f"{BASE_URL}{url}"

    try:
        start = time.time()
        response = session.get(full_url, timeout=10)
        elapsed_ms = (time.time() - start) * 1000

        success = response.status_code == 200
        error = None if success else f"HTTP {response.status_code}"
        stats.record_request(url, success, elapsed_ms, error, is_write=False)

    except Exception as e:
        stats.record_request(url, False, 0, str(e), is_write=False)


def simulate_volunteer(user_id, duration_seconds, stats, include_writes=False, write_ratio=0.2, min_delay=1.0, max_delay=3.0):
    """Simulate a single volunteer browsing the app"""
    end_time = time.time() + duration_seconds
    session = requests.Session()

    while time.time() < end_time:
        # Decide whether to read or write
        if include_writes and random.random() < write_ratio:
            do_write(session, stats)
        else:
            do_read(session, stats)

        # Random delay between actions (simulates human behavior)
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)


def fetch_metrics():
    """Get current metrics from the app"""
    try:
        response = requests.get(f"{BASE_URL}/metrics", timeout=5)
        return response.json()
    except:
        return None


def print_header():
    print("\n" + "=" * 70)
    print("TNT Load Test")
    print("=" * 70)


def print_live_stats(stats, metrics, elapsed):
    """Print live statistics"""
    summary = stats.get_summary()
    if not summary:
        return

    writes_str = f" W:{summary['writes']}" if summary['writes'] > 0 else ""
    print(f"\r[{elapsed:3.0f}s] "
          f"Req: {summary['total_requests']:4d}{writes_str} | "
          f"Avg: {summary['avg_response_ms']:5.0f}ms | "
          f"Fail: {summary['failed']:2d} | ", end="")

    if metrics:
        print(f"Goog: {metrics.get('google_calls_last_minute', '?')}/m | "
              f"Cache: {metrics.get('cache_hit_rate', '?')} | "
              f"Err: {metrics.get('rate_limit_errors', 0)}", end="")
    print("    ", end="", flush=True)


def run_load_test(num_users, duration_seconds, include_writes, write_ratio, min_delay, max_delay):
    print_header()
    print(f"Users: {num_users}")
    print(f"Duration: {duration_seconds} seconds")
    print(f"Delay between actions: {min_delay}-{max_delay} seconds")
    print(f"Include writes: {include_writes}", end="")
    if include_writes:
        print(f" ({int(write_ratio * 100)}% write ratio)")
        print("📝 Writes go to 'Load Test Entries' sheet (not real data)")
    else:
        print()
    print("-" * 70)

    # Check app is running
    try:
        requests.get(f"{BASE_URL}/", timeout=5)
    except:
        print(f"❌ Error: Cannot connect to {BASE_URL}")
        print("   Make sure the app is running: python tnt.py")
        return

    # Reset metrics for fresh test
    try:
        requests.get(f"{BASE_URL}/test/reset", timeout=5)
        print("Metrics reset ✓")
    except:
        pass

    # Get initial metrics
    initial_metrics = fetch_metrics()
    if initial_metrics:
        print(f"Initial state: {initial_metrics.get('cache_hits', 0)} cache hits, "
              f"{initial_metrics.get('cache_misses', 0)} misses")

    stats = LoadTestStats()
    threads = []

    print(f"\nStarting {num_users} simulated volunteers...")
    print("-" * 70)

    start_time = time.time()

    # Start volunteer threads
    for i in range(num_users):
        t = threading.Thread(
            target=simulate_volunteer,
            args=(i, duration_seconds, stats, include_writes, write_ratio, min_delay, max_delay)
        )
        t.daemon = True
        t.start()
        threads.append(t)
        time.sleep(0.1)  # Stagger starts slightly

    # Monitor progress
    while any(t.is_alive() for t in threads):
        elapsed = time.time() - start_time
        metrics = fetch_metrics()
        print_live_stats(stats, metrics, elapsed)
        time.sleep(1)

    # Final results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    summary = stats.get_summary()
    final_metrics = fetch_metrics()

    print(f"\nClient-side stats:")
    print(f"  Total requests:     {summary['total_requests']}")
    print(f"  Reads:              {summary['reads']}")
    print(f"  Writes:             {summary['writes']}")
    print(f"  Succeeded:          {summary['succeeded']}")
    print(f"  Failed:             {summary['failed']}")
    print(f"  Avg response time:  {summary['avg_response_ms']:.0f}ms")
    print(f"  Max response time:  {summary['max_response_ms']:.0f}ms")
    print(f"  Requests/second:    {summary['total_requests'] / duration_seconds:.1f}")

    if final_metrics and initial_metrics:
        new_google_reads = final_metrics['total_google_reads'] - initial_metrics.get('total_google_reads', 0)
        new_google_writes = final_metrics['total_writes'] - initial_metrics.get('total_writes', 0)
        new_google_calls = new_google_reads + new_google_writes
        new_cache_hits = final_metrics['cache_hits'] - initial_metrics.get('cache_hits', 0)
        new_errors = final_metrics['rate_limit_errors'] - initial_metrics.get('rate_limit_errors', 0)

        print(f"\nServer-side stats (Google Sheets API):")
        print(f"  Google reads:       {new_google_reads}")
        print(f"  Google writes:      {new_google_writes}")
        print(f"  Total Google calls: {new_google_calls}")
        print(f"  Cache hits:         {new_cache_hits}")
        print(f"  Cache hit rate:     {final_metrics['cache_hit_rate']}")
        print(f"  Rate limit errors:  {new_errors}")
        print(f"  Google calls/min:   {new_google_calls / (duration_seconds / 60):.1f}")

        # Assessment
        print(f"\n{'=' * 70}")
        google_per_min = new_google_calls / (duration_seconds / 60)
        if google_per_min < 30:
            print("✅ SAFE: Well under the 60/min Google API limit")
            headroom = 60 / google_per_min if google_per_min > 0 else float('inf')
            print(f"   You could handle ~{headroom:.1f}x more traffic")
        elif google_per_min < 50:
            print("⚠️  CAUTION: Getting close to the 60/min limit")
            print("   Consider increasing cache TTL or reducing page loads")
        else:
            print("❌ DANGER: At or above the 60/min limit")
            print("   You will hit rate limits with this traffic pattern")

    if stats.errors:
        print(f"\nErrors encountered:")
        for error, count in stats.errors.items():
            print(f"  {error}: {count}")

    if include_writes and summary['writes'] > 0:
        print(f"\n💡 Tip: Clear test data with: curl -X POST {BASE_URL}/test/write/clear")

    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load test for TNT app")
    parser.add_argument("--users", type=int, default=10, help="Number of simulated volunteers (default: 10)")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds (default: 60)")
    parser.add_argument("--min-delay", type=float, default=1.0, help="Min seconds between user actions (default: 1.0)")
    parser.add_argument("--max-delay", type=float, default=3.0, help="Max seconds between user actions (default: 3.0)")
    parser.add_argument("--include-writes", action="store_true", help="Include real write operations to test sheet")
    parser.add_argument("--write-ratio", type=float, default=0.2, help="Ratio of writes to total actions (default: 0.2 = 20%%)")
    parser.add_argument("--base-url", default=BASE_URL, help=f"Base URL (default: {BASE_URL})")

    args = parser.parse_args()
    BASE_URL = args.base_url

    run_load_test(
        num_users=args.users,
        duration_seconds=args.duration,
        include_writes=args.include_writes,
        write_ratio=args.write_ratio,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
    )
