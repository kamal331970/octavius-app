import anthropic
import os
import json
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from notion_client import Client
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_PAGE_ID = os.environ.get("NOTION_PAGE_ID")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = os.environ.get("GOOGLE_REFRESH_TOKEN")

def get_creds():
    return Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET
    )

def get_events():
    svc = build("calendar", "v3", credentials=get_creds())
    now = datetime.utcnow().isoformat() + "Z"
    end = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
    items = svc.events().list(
        calendarId="primary", timeMin=now, timeMax=end,
        maxResults=5, singleEvents=True, orderBy="startTime"
    ).execute().get("items", [])
    if not items:
        return "Aucun evenement aujourd hui."
    out = []
    for e in items:
        s = e["start"].get("dateTime", e["start"].get("date"))
        out.append("- " + e["summary"] + " a " + str(s))
    return "\n".join(out)

def make_event(title, date_str, time_str):
    svc = build("calendar", "v3", credentials=get_creds())
    try:
        d = datetime.strptime(date_str + " " + time_str, "%Y-%m-%d %H:%M")
    except:
        d = datetime.utcnow() + timedelta(days=1)
        d = d.replace(hour=10, minute=0)
    ev = {
        "summary": title,
        "start": {"dateTime": d.isoformat(), "timeZone": "Europe/Paris"},
        "end": {"dateTime": (d + timedelta(hours=1)).isoformat(), "timeZone": "Europe/Paris"}
    }
    svc.events().insert(calendarId="primary", body=ev).execute()
    return "RDV cree: " + title + " le " + d.strftime("%d/%m/%Y a %H:%M")

def get_emails():
    svc = build("gmail", "v1", credentials=get_creds())
    results = svc.users().messages().list(userId="me", labelIds=["UNREAD"], maxResults=5).execute()
    messages = results.get("messages", [])
    if not messages:
        return "Aucun email non lu."
    out = []
    for m in messages:
        msg = svc.users().messages().get(userId="me", id=m["id"], format="metadata", metadataHeaders=["From", "Subject"]).execute()
        headers = {h["name"]:
