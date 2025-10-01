import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

def get_google_creds():
    """Get Google credentials either from file or environment variable"""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    if 'GOOGLE_SHEETS_CREDS' in os.environ:
        creds_dict = json.loads(os.environ['GOOGLE_SHEETS_CREDS'])
        return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        return ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)

def get_spreadsheet():
    """Get the Google Sheets spreadsheet"""
    creds = get_google_creds()
    client = gspread.authorize(creds)
    sheet_name = os.environ.get('SHEET_NAME', 'TNT_App_Data')
    return client.open(sheet_name)