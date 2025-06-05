# Deploying to Render

## Prerequisites
1. A GitHub account with your repository pushed
2. A Render account (sign up at https://render.com)
3. Your Google Sheets credentials

## Steps

1. **Sign up for Render**
   - Go to https://render.com
   - Sign up with your GitHub account

2. **Create a New Web Service**
   - Click "New +"
   - Select "Web Service"
   - Connect your GitHub repository
   - Choose the repository with your TNT app

3. **Configure the Web Service**
   - Name: `tnt-reading-tracker` (or your preferred name)
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn tnt:app`
   - Select the free tier

4. **Set Environment Variables**
   In the Render dashboard, add these environment variables:
   - `GOOGLE_SHEETS_CREDS`: Paste the entire contents of your client_secret.json
   - `SHEET_NAME`: Your Google Sheet name (e.g., 'TNT_App_Data')

5. **Deploy**
   - Click "Create Web Service"
   - Render will automatically deploy your application
   - You'll get a URL like `https://your-app-name.onrender.com`

## Updating Your Application
- Push changes to your GitHub repository
- Render will automatically redeploy your application

## Troubleshooting
- Check the Render logs if the application fails to start
- Verify your environment variables are set correctly
- Ensure your Google Sheet is shared with the service account email 