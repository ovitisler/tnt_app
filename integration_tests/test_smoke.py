"""
Smoke tests against a deployed instance of the app (Vercel preview or production).

Read-only: never writes, never calls /test/* endpoints, so it's safe to run
against deployments that share the production sheet and Redis cache.

Usage:
    SMOKE_BASE_URL=https://tnt-app-five.vercel.app pytest integration_tests/ -v

Set VERCEL_AUTOMATION_BYPASS_SECRET to reach protected preview deployments.
"""
import os
import re

import pytest
import requests

BASE_URL = os.environ.get('SMOKE_BASE_URL', '').rstrip('/')
BYPASS_SECRET = os.environ.get('VERCEL_AUTOMATION_BYPASS_SECRET')

pytestmark = pytest.mark.skipif(not BASE_URL, reason='SMOKE_BASE_URL not set')


@pytest.fixture(scope='module')
def session():
    s = requests.Session()
    if BYPASS_SECRET:
        s.headers['x-vercel-protection-bypass'] = BYPASS_SECRET
    return s


def get_page(session, path):
    """GET a page and assert it rendered successfully (no redirect, no error page)."""
    response = session.get(f'{BASE_URL}{path}', timeout=30, allow_redirects=False)
    assert response.status_code == 200, (
        f'{path} returned {response.status_code} '
        f'(Location: {response.headers.get("Location")})'
    )
    assert 'error-page' not in response.text, f'{path} rendered the error page'
    return response.text


def first_link(html, pattern, path):
    """Find the first onclick link matching pattern in a page's HTML."""
    match = re.search(pattern, html)
    assert match, f'No link matching {pattern!r} found on {path}'
    return match.group(0)


@pytest.mark.parametrize('path', ['/', '/attendance', '/progress'])
def test_tab_pages_load(session, path):
    get_page(session, path)


def test_home_date_and_team_pages_load(session):
    home = get_page(session, '/')
    date_path = first_link(home, r"/home/\d{4}-\d{2}-\d{2}(?=')", '/')
    date_page = get_page(session, date_path)
    team_path = first_link(date_page, r"/home/[^'/]+/team/[^']+(?=')", date_path)
    get_page(session, team_path)


def test_attendance_date_and_team_pages_load(session):
    attendance = get_page(session, '/attendance')
    date_path = first_link(attendance, r"/attendance/\d{4}-\d{2}-\d{2}(?=')", '/attendance')
    date_page = get_page(session, date_path)
    team_path = first_link(date_page, r"/attendance/[^'/]+/team/[^']+(?=')", date_path)
    get_page(session, team_path)


def test_student_progress_page_loads(session):
    progress = get_page(session, '/progress')
    student_path = first_link(progress, r"/progress/student/[^']+(?=')", '/progress')
    get_page(session, student_path)


def test_metrics_show_cache_populated(session):
    # Load a page first so the static sheets are guaranteed to be cached.
    get_page(session, '/')
    response = session.get(f'{BASE_URL}/metrics', timeout=30)
    assert response.status_code == 200
    metrics = response.json()
    assert 'Schedule' in metrics['cached_sheets']
    assert 'Master Roster' in metrics['cached_sheets']
