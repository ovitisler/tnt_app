# TNT App — Claude Context

Flask web app for tracking a church kids' reading program (TNT). Tracks attendance and reading section completions per kid, per team, per date. Data lives entirely in Google Sheets.

## Running Locally

```bash
source .venv/bin/activate
python tnt.py        # http://localhost:5001
pytest tests/ -q    # run tests
```

## Architecture

**Entry point:** `tnt.py` — creates Flask app, registers route blueprints, adds Jinja filters.

**Data layer:** `models/` — all sheet I/O goes through here, never directly from routes.
- `sheets.py` — sheet names as constants, list of which sheets are static (cached long-term) vs dynamic
- `data.py` — all read/write functions (`get_*`, `insert_*`, `update_*`, `upsert_*`)
- `cache.py` — stale-while-revalidate caching; background threads refresh data
- `fields.py` — column name constants (`NAME`, `DATE`, `SECTION`, etc.)
- `utils.py` — date helpers (`get_today()`, `date_to_mmdd()`, `find_closest_date_url()`)
- `test_mode.py` — `DATE_OVERRIDE` string for testing with historical data; set to `None` in prod

**Routes:** `routes/` — each file registers routes on the Flask app via `register_*_routes(app)`.
- `home.py` — schedule view + record completed sections flow
- `attendance.py` — attendance check-in flow
- `progress.py` — per-student progress view and section edit
- `testing.py` — dev/debug endpoints

**Templates:** `templates/` — Jinja2, mobile-first. Two base layouts:
- `base.html` — standard page with header/back button
- `fullscreen_base.html` — form pages (no nav chrome)

## Key Data Flows

### Record a Completed Section (home tab)
1. Pick date → pick team → "Record Section" → `record_section_kid_picker` (pick kid)
2. → `record_section_list` — shows all Book Sections with coalesced status chips (Main ✓, 🥈, 🥇)
3. → `record_section_form` — greyed kid/date/section + toggles only for credits not yet recorded
4. POST `/submit_section` → `upsert_completed_section()` — updates today's row if exists, inserts if not

### Attendance Check-In
1. Pick date → pick team → `team_attendance_details` — shows ALL roster kids (checked-in: chips; not: dashed row)
2. Tap unchecked kid → `checkin_form_for_kid` → POST `/submit_checkin`
3. Tap checked-in kid → `kid_attendance_details` → POST `/edit_attendance`

### Student Progress (progress tab)
1. Search by name → `student_progress` — coalesced section list (one row per section, merged across dates)
2. Tap section → `student_section_log` — audit log of all raw records for that section
3. Tap record → `student_section_details` → POST `/edit_progress_section`

## Upsert Logic
`upsert_completed_section` checks for an existing row matching (Name, Date, Section) for today. If found, updates it; if not, inserts a new row. This prevents duplicate rows for the same kid/day/section.

## Coalescing
Multiple rows can exist per (kid, section) across different dates. The UI merges them:
- `main_date` — date the section was marked complete
- `silver_date` / `gold_date` — dates those credits were recorded (may differ from main)

## Date Handling
- `get_today()` in `utils.py` returns `DATE_OVERRIDE` (from `test_mode.py`) if set, else real today
- URL date format: `YYYY-MM-DD` (e.g. `2025-10-23`)
- Display date format: `January 15, 2025` (as stored in Google Sheets)
- `date_to_mmdd` Jinja filter: formats ISO date as `m/d` for compact display

## CSS Conventions
- `.section-row` — standard list item with flex layout
- `.section-row.complete` — gold gradient background (all 3 credits done); defined BEFORE `:hover` rule so hover can override
- `.back-btn` — pill-style back button in the header (defined in `base.html`)
- Chips: inline `style=` spans with green/grey backgrounds; `white-space: nowrap` on container

## Google Sheets Structure
- **Schedule** — reading schedule dates and themes
- **Attendance** — one row per kid per date (check-in fields)
- **Attendance Totals** — aggregated per team per date
- **Completed Sections** — one row per action (Name, Date, Section, Silver Credit, Gold Credit, Team)
- **Book Sections** — single column `Section`, master list of all sections
- **Roster** — kids with their team (`Group` column)

## Pushing to GitHub
Remote is `https://ovitisler@github.com/ovitisler/tnt_app.git`. Needs a PAT:
```bash
git push https://ovitisler:<PAT>@github.com/ovitisler/tnt_app.git main
```

## Testing
Tests are in `tests/`. They mock gspread and all Google Sheets calls. No real sheet access needed.
- Mock the function as imported in the route module, e.g. `@patch('routes.home.upsert_completed_section')`
- `DATE_OVERRIDE` in `test_mode.py` affects `get_today()` — keep it set to a date with test data
