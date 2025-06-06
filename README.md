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
git clone <your-repo-url>
cd tnt
```

2. Install dependencies:
```bash
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
python tnt.py
```

## Environment Variables
The following environment variables need to be set:
- `GOOGLE_SHEETS_CREDS`: The contents of your client_secret.json file (for production)
- `SHEET_NAME`: The name of your Google Sheet (default: 'TNT_App_Data')

## Deployment
This application is configured for deployment on Render. See deployment instructions in DEPLOYMENT.md.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 