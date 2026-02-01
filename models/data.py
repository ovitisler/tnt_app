"""
Abstract data layer for record storage.
Routes should use this module instead of sheets.py directly.
Currently backed by Google Sheets, but could be swapped for a database.
"""
from datetime import datetime

from models.fields import TIMESTAMP
from models.sheets import (
    get_sheet_data as _get_sheet_data,
    get_worksheet,
    _cache,
    _trigger_background_refresh,
    INVALIDATION_MAP,
)


def get_records(table: str) -> list[dict]:
    """
    Get all records from a table.
    Uses caching with stale-while-revalidate pattern.
    """
    return _get_sheet_data(table)


def insert_record(table: str, data: dict) -> dict:
    """
    Insert a new record into a table.
    Automatically adds timestamp if not present.
    Returns the inserted data.
    """
    # Add timestamp if not present
    if TIMESTAMP not in data:
        data[TIMESTAMP] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Write to storage
    worksheet = get_worksheet(table)
    headers = worksheet.row_values(1)

    # Build row in correct order based on headers
    row = [data.get(header, '') for header in headers]
    worksheet.append_row(row, value_input_option='USER_ENTERED')

    # Update cache
    _cache.append_row(table, data)

    # Trigger refresh for computed/related tables
    _refresh_related_tables(table)

    return data


def update_record(table: str, match_fn, updates: dict) -> bool:
    """
    Update a record that matches the given predicate.
    Returns True if a record was found and updated.
    """
    worksheet = get_worksheet(table)
    all_records = worksheet.get_all_records()
    headers = worksheet.row_values(1)

    for i, record in enumerate(all_records):
        if match_fn(record):
            row_num = i + 2  # +2: 1-indexed and skip header

            # Update each field in storage
            for field_name, value in updates.items():
                try:
                    col_index = headers.index(field_name) + 1
                    worksheet.update_cell(row_num, col_index, value)
                except ValueError:
                    continue

            # Update cache
            _cache.update_row(table, match_fn, updates)

            # Trigger refresh for computed/related tables
            _refresh_related_tables(table)

            return True

    return False


def _refresh_related_tables(table: str):
    """Trigger background refresh for tables that depend on this one."""
    if table in INVALIDATION_MAP:
        for related_table in INVALIDATION_MAP[table]:
            if related_table != table:
                _trigger_background_refresh(related_table)
