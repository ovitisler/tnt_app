"""
Abstract data layer for record storage.
Routes should use this module for all data operations.
"""
from datetime import datetime

from models.fields import TIMESTAMP
from models.sheets import (
    get_sheet_data as _get_sheet_data,
    get_worksheet as _get_worksheet,
    _cache,
    _trigger_background_refresh,
    INVALIDATION_MAP,
    SCHEDULE_SHEET,
    ATTENDANCE_SCHEDULE_SHEET,
    MASTER_ROSTER_SHEET,
    WEEKLY_TOTALS_SHEET,
    WEEKLY_ATTENDANCE_TOTALS_SHEET,
    COMPLETED_SECTIONS_SHEET,
    ATTENDANCE_ENTRIES_SHEET,
    RateLimitError,
    get_metrics,
)


# =============================================================================
# Read Operations
# =============================================================================

def get_schedule():
    """Get the main schedule data."""
    return _get_sheet_data(SCHEDULE_SHEET)


def get_attendance_schedule():
    """Get the attendance schedule data."""
    return _get_sheet_data(ATTENDANCE_SCHEDULE_SHEET)


def get_roster():
    """Get all students from the master roster."""
    return _get_sheet_data(MASTER_ROSTER_SHEET)


def get_weekly_totals():
    """Get weekly section completion totals."""
    return _get_sheet_data(WEEKLY_TOTALS_SHEET)


def get_attendance_totals():
    """Get weekly attendance totals."""
    return _get_sheet_data(WEEKLY_ATTENDANCE_TOTALS_SHEET)


def get_completed_sections():
    """Get all completed section records."""
    return _get_sheet_data(COMPLETED_SECTIONS_SHEET)


def get_attendance_entries():
    """Get all attendance entry records."""
    return _get_sheet_data(ATTENDANCE_ENTRIES_SHEET)


# =============================================================================
# Write Operations
# =============================================================================

def insert_completed_section(data: dict) -> dict:
    """Record a completed section for a student."""
    return _insert_record(COMPLETED_SECTIONS_SHEET, data)


def insert_attendance_entry(data: dict) -> dict:
    """Record an attendance entry for a student."""
    return _insert_record(ATTENDANCE_ENTRIES_SHEET, data)


def update_completed_section(match_fn, updates: dict) -> bool:
    """Update a completed section record."""
    return _update_record(COMPLETED_SECTIONS_SHEET, match_fn, updates)


def update_attendance_entry(match_fn, updates: dict) -> bool:
    """Update an attendance entry record."""
    return _update_record(ATTENDANCE_ENTRIES_SHEET, match_fn, updates)


# =============================================================================
# Internal Helpers
# =============================================================================

def _insert_record(table: str, data: dict) -> dict:
    """Insert a new record into a table."""
    if TIMESTAMP not in data:
        data[TIMESTAMP] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    worksheet = _get_worksheet(table)
    headers = worksheet.row_values(1)

    row = [data.get(header, '') for header in headers]
    worksheet.append_row(row, value_input_option='USER_ENTERED')

    _cache.append_row(table, data)
    _refresh_related_tables(table)

    return data


def _update_record(table: str, match_fn, updates: dict) -> bool:
    """Update a record that matches the given predicate."""
    worksheet = _get_worksheet(table)
    all_records = worksheet.get_all_records()
    headers = worksheet.row_values(1)

    for i, record in enumerate(all_records):
        if match_fn(record):
            row_num = i + 2  # +2: 1-indexed and skip header

            for field_name, value in updates.items():
                try:
                    col_index = headers.index(field_name) + 1
                    worksheet.update_cell(row_num, col_index, value)
                except ValueError:
                    continue

            _cache.update_row(table, match_fn, updates)
            _refresh_related_tables(table)

            return True

    return False


def _refresh_related_tables(table: str):
    """Trigger background refresh for tables that depend on this one."""
    if table in INVALIDATION_MAP:
        for related_table in INVALIDATION_MAP[table]:
            if related_table != table:
                _trigger_background_refresh(related_table)
