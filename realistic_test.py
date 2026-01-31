#!/usr/bin/env python3
"""
Realistic volunteer simulation for TNT Reading Teams Tracker

Simulates actual volunteer behavior patterns:
- Bursts of activity (browse, record, browse)
- Idle periods (helping kids, chatting)
- Occasional rapid writes (recording multiple sections)

Usage:
    python realistic_test.py                     # 10 volunteers, 30 minutes
    python realistic_test.py --users 25          # 25 volunteers
    python realistic_test.py --duration 60       # Run for 60 minutes
    python realistic_test.py --active-ratio 0.5  # 50% of users active at any time
"""

import argparse
import random
import time
import threading
import requests
from collections import defaultdict
from datetime import datetime
from enum import Enum

# Configuration
BASE_URL = "http://localhost:5001"

# Pages volunteers visit
PAGES = {
    'home': ["/", "/home/2025-09-17"],
    'team': ["/home/2025-09-17/team/Green", "/home/2025-09-17/team/Blue", "/home/2025-09-17/team/Red"],
    'attendance': ["/attendance", "/attendance/2025-09-17", "/attendance/2025-09-17/team/Green"],
    'progress': ["/progress", "/progress/student/Test%20Student"],
}


class VolunteerState(Enum):
    BROWSING = "browsing"      # Looking at screens
    RECORDING = "recording"    # Recording sections (writes)
    IDLE = "idle"              # Helping kids, not using app


class RealisticStats:
    def __init__(self):
        self.lock = threading.Lock()
        self.reads = 0
        self.writes = 0
        self.failed = 0
        self.response_times = []
        self.state_times = defaultdict(float)
        self.activity_log = []

    def record(self, action, success, response_time):
        with self.lock:
            if action == 'read':
                self.reads += 1
            else:
                self.writes += 1
            if not success:
                self.failed += 1
            if response_time > 0:
                self.response_times.append(response_time)

    def log_state_change(self, user_id, old_state, new_state):
        with self.lock:
            self.activity_log.append({
                'time': datetime.now().strftime('%H:%M:%S'),
                'user': user_id,
                'from': old_state,
                'to': new_state
            })

    def get_summary(self):
        with self.lock:
            avg_response = sum(self.response_times) / len(self.response_times) if self.response_times else 0
            return {
                'reads': self.reads,
                'writes': self.writes,
                'total': self.reads + self.writes,
                'failed': self.failed,
                'avg_response_ms': avg_response,
            }


def do_read(session, stats):
    """Single read operation"""
    category = random.choice(list(PAGES.keys()))
    url = random.choice(PAGES[category])
    full_url = f"{BASE_URL}{url}"

    try:
        start = time.time()
        response = session.get(full_url, timeout=10)
        elapsed_ms = (time.time() - start) * 1000
        stats.record('read', response.status_code == 200, elapsed_ms)
        return response.status_code == 200
    except:
        stats.record('read', False, 0)
        return False


def do_write(session, stats):
    """Single write operation"""
    try:
        start = time.time()
        response = session.post(f"{BASE_URL}/test/write", json={}, timeout=15)
        elapsed_ms = (time.time() - start) * 1000
        stats.record('write', response.status_code == 200, elapsed_ms)
        return response.status_code == 200
    except:
        stats.record('write', False, 0)
        return False


def simulate_volunteer(user_id, duration_minutes, stats, active_ratio):
    """
    Simulate realistic volunteer behavior:
    - Browse around (10-15 reads over 30-60 seconds)
    - Record 1-4 sections (writes)
    - Go idle for 1-5 minutes
    - Repeat
    """
    end_time = time.time() + (duration_minutes * 60)
    session = requests.Session()
    state = VolunteerState.IDLE

    # Stagger start times - not everyone arrives at once
    initial_delay = random.uniform(0, 60)
    time.sleep(initial_delay)

    while time.time() < end_time:
        # Decide if this volunteer is "active" right now
        # Simulates some volunteers taking breaks, chatting, etc.
        if random.random() > active_ratio:
            time.sleep(random.uniform(30, 120))  # Inactive for 30s-2min
            continue

        # === BROWSING PHASE ===
        # Volunteer opens app, looks around
        old_state = state
        state = VolunteerState.BROWSING
        if old_state != state:
            stats.log_state_change(user_id, old_state.value, state.value)

        num_reads = random.randint(8, 15)
        for _ in range(num_reads):
            do_read(session, stats)
            time.sleep(random.uniform(0.5, 2.0))  # Quick browsing

        # === RECORDING PHASE ===
        # Volunteer records sections for kids
        state = VolunteerState.RECORDING
        stats.log_state_change(user_id, VolunteerState.BROWSING.value, state.value)

        # Usually 1-2 writes, occasionally a burst of 3-4
        if random.random() < 0.2:  # 20% chance of burst
            num_writes = random.randint(3, 5)
        else:
            num_writes = random.randint(1, 2)

        for _ in range(num_writes):
            do_write(session, stats)
            # Quick reads between writes (checking the result)
            time.sleep(random.uniform(0.5, 1.5))
            do_read(session, stats)
            time.sleep(random.uniform(1.0, 3.0))

        # === IDLE PHASE ===
        # Volunteer puts phone down, helps kids
        state = VolunteerState.IDLE
        stats.log_state_change(user_id, VolunteerState.RECORDING.value, state.value)

        idle_time = random.uniform(60, 180)  # 1-3 minutes idle
        time.sleep(idle_time)


def fetch_metrics():
    """Get current metrics from the app"""
    try:
        response = requests.get(f"{BASE_URL}/metrics", timeout=5)
        return response.json()
    except:
        return None


def print_status(stats, metrics, elapsed_min, duration_min):
    """Print current status"""
    summary = stats.get_summary()
    pct = (elapsed_min / duration_min) * 100

    print(f"\r[{elapsed_min:.1f}/{duration_min}min {pct:.0f}%] "
          f"R:{summary['reads']} W:{summary['writes']} "
          f"Fail:{summary['failed']} | ", end="")

    if metrics:
        print(f"Goog:{metrics.get('google_calls_last_minute', '?')}/m "
              f"Cache:{metrics.get('cache_hit_rate', '?')} "
              f"Err:{metrics.get('rate_limit_errors', 0)}", end="")
    print("      ", end="", flush=True)


def run_realistic_test(num_users, duration_minutes, active_ratio):
    print("\n" + "=" * 70)
    print("TNT Realistic Volunteer Simulation")
    print("=" * 70)
    print(f"Volunteers: {num_users}")
    print(f"Duration: {duration_minutes} minutes")
    print(f"Active ratio: {int(active_ratio * 100)}% of users active at any time")
    print(f"Behavior: Browse (10-15 reads) → Record (1-4 writes) → Idle (1-3 min)")
    print("-" * 70)

    # Check app is running
    try:
        requests.get(f"{BASE_URL}/", timeout=5)
    except:
        print(f"❌ Cannot connect to {BASE_URL}")
        print("   Make sure the app is running: python tnt.py")
        return

    # Reset metrics for fresh test
    try:
        requests.get(f"{BASE_URL}/test/reset", timeout=5)
        print("Metrics reset ✓")
    except:
        pass

    initial_metrics = fetch_metrics()
    stats = RealisticStats()
    threads = []

    print(f"\nStarting {num_users} simulated volunteers (staggered over 60s)...")
    print("-" * 70)

    start_time = time.time()

    # Start volunteer threads
    for i in range(num_users):
        t = threading.Thread(
            target=simulate_volunteer,
            args=(i, duration_minutes, stats, active_ratio)
        )
        t.daemon = True
        t.start()
        threads.append(t)

    # Monitor progress
    while any(t.is_alive() for t in threads):
        elapsed_min = (time.time() - start_time) / 60
        metrics = fetch_metrics()
        print_status(stats, metrics, elapsed_min, duration_minutes)
        time.sleep(2)

    # Final results
    elapsed_min = (time.time() - start_time) / 60
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    summary = stats.get_summary()
    final_metrics = fetch_metrics()

    print(f"\nSimulation stats:")
    print(f"  Duration:           {elapsed_min:.1f} minutes")
    print(f"  Total reads:        {summary['reads']}")
    print(f"  Total writes:       {summary['writes']}")
    print(f"  Read/write ratio:   {summary['reads']/(summary['writes'] or 1):.1f}:1")
    print(f"  Failed requests:    {summary['failed']}")
    print(f"  Avg response time:  {summary['avg_response_ms']:.0f}ms")
    print(f"  Requests/minute:    {summary['total'] / elapsed_min:.1f}")

    if final_metrics and initial_metrics:
        new_google_reads = final_metrics['total_google_reads'] - initial_metrics.get('total_google_reads', 0)
        new_google_writes = final_metrics['total_writes'] - initial_metrics.get('total_writes', 0)
        new_google_calls = new_google_reads + new_google_writes
        new_cache_hits = final_metrics['cache_hits'] - initial_metrics.get('cache_hits', 0)
        new_errors = final_metrics['rate_limit_errors'] - initial_metrics.get('rate_limit_errors', 0)

        print(f"\nGoogle Sheets API stats:")
        print(f"  Google reads:       {new_google_reads}")
        print(f"  Google writes:      {new_google_writes}")
        print(f"  Total Google calls: {new_google_calls}")
        print(f"  Cache hits:         {new_cache_hits}")
        print(f"  Cache hit rate:     {final_metrics['cache_hit_rate']}")
        print(f"  Rate limit errors:  {new_errors}")
        print(f"  Avg Google/minute:  {new_google_calls / elapsed_min:.1f}")

        print(f"\n{'=' * 70}")
        google_per_min = new_google_calls / elapsed_min
        if new_errors == 0 and google_per_min < 40:
            print("✅ PASSED: No rate limit errors, sustainable API usage")
            print(f"   Average {google_per_min:.1f} Google calls/min (limit: 60)")
        elif new_errors < 5:
            print("⚠️  MARGINAL: Few rate limit errors, might need tuning")
            print(f"   Consider increasing cache TTL if errors persist")
        else:
            print("❌ FAILED: Too many rate limit errors")
            print(f"   {new_errors} errors over {elapsed_min:.1f} minutes")

    if summary['writes'] > 0:
        print(f"\n💡 Clear test data: curl -X POST {BASE_URL}/test/write/clear")

    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Realistic volunteer simulation")
    parser.add_argument("--users", type=int, default=10, help="Number of volunteers (default: 10)")
    parser.add_argument("--duration", type=int, default=30, help="Duration in minutes (default: 30)")
    parser.add_argument("--active-ratio", type=float, default=0.7, help="Ratio of users active at any time (default: 0.7)")
    parser.add_argument("--base-url", default=BASE_URL, help=f"Base URL (default: {BASE_URL})")

    args = parser.parse_args()
    BASE_URL = args.base_url

    run_realistic_test(
        num_users=args.users,
        duration_minutes=args.duration,
        active_ratio=args.active_ratio,
    )
