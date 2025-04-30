# youtube_uploader1.py - Upload and schedule YouTube videos

import os
import pickle
from datetime import datetime
import pytz

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from apscheduler.schedulers.background import BackgroundScheduler

# OAuth Scopes for YouTube access
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.readonly"
]

CLIENT_SECRETS = "client_secret.json"
TOKEN_FILE = "token_upload.pickle"

# Background scheduler for scheduling uploads
scheduler = BackgroundScheduler()
scheduler.start()

# Authenticate and return YouTube API service
def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
        creds = flow.run_local_server(port=8080)
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)

# Upload a video immediately
def upload_video(file_path, title, description, tags, privacy, publish_at=None):
    youtube = get_authenticated_service()

    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags
        },
        "status": {
            "privacyStatus": privacy  # 'private', 'unlisted', or 'public'
        }
    }

    if publish_at and privacy == "private":
        request_body["status"]["publishAt"] = publish_at
        request_body["status"]["selfDeclaredMadeForKids"] = False

    media = MediaFileUpload(file_path, mimetype="video/*", resumable=True)

    response_upload = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    ).execute()

    print("Upload successful! Video ID:", response_upload["id"])
    return response_upload["id"]

# Schedule a video upload at a future time (UTC time format: "2025-04-25T12:00:00")
def schedule_upload(file_path, title, description, tags, privacy, publish_at):
    dt = datetime.strptime(publish_at, "%Y-%m-%dT%H:%M:%S")
    dt_utc = pytz.utc.localize(dt)

    scheduler.add_job(
        upload_video,
        'date',
        run_date=dt_utc,
        args=[file_path, title, description, tags, privacy, None],
        id="upload_job_" + dt.strftime("%Y%m%d%H%M%S")
    )
    print("Upload scheduled for:", dt_utc)
