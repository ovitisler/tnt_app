# TNT Reading Teams Tracker

A Flask web application to track reading teams and their progress.

## Features
- Track students across different teams
- Record reading sections completed
- View team standings and individual progress
- Easy student management interface

## Setup

1. Clone the repository:
```bash
git clone https://github.com/ovitisler/tnt_app.git
cd tnt
```

2. Create virtual environment and install dependencies:
```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Or with standard tools:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Set up Google Sheets:
- Create a Google Cloud Project
- Enable Google Sheets API
- Create service account credentials
- Download the credentials as `client_secret.json`
- Share your Google Sheet with the service account email

4. Run the application:
```bash
source .venv/bin/activate  # if not already activated
python tnt.py
```
The app will be available at `http://localhost:5001`

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_SHEETS_CREDS` | Yes (prod) | — | Contents of `client_secret.json` |
| `SHEET_NAME` | No | `TNT_App_Data` | Google Sheet name |
| `CACHE_BACKEND` | No | `memory` | `memory` (in-process) or `redis` (Vercel KV) |
| `REDIS_URL` | If redis | — | Vercel Redis connection string (auto-set by Vercel) |

## Testing

```bash
source .venv/bin/activate
pytest tests/ -q
```

## Deployment
Deployed on Vercel. See DEPLOYMENT.md for setup instructions.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 