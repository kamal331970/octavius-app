import anthropic
import os
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

def get_google_creds():
    return Credentials(token=None, refresh_token=GOOGLE_REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=GOOGLE_CLIENT_ID, client_secret=GOOGLE_CLIENT_SECRET)

def get_calendar_events():
    service = build("calendar", "v3", credentials=get_google_creds())
    now = datetime.utcnow().isoformat() + "Z"
    end = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
    events = service.events().list(calendarId="primary", timeMin=now, timeMax=end, maxResults=5, singleEvents=True, orderBy="startTime").execute().get("items", [])
    if not events: return "Aucun evenement aujourd hui."
    return "".join([f"- {e['summary']} a {e['start'].get('dateTime', e['start'].get('date'))}
" for e in events])

def create_calendar_event(title, date_str, time_str="10:00"):
    service = build("calendar", "v3", credentials=get_google_creds())
    try:
        date = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except:
        date = datetime.utcnow() + timedelta(days=1)
    event = {"summary": title, "start": {"dateTime": date.isoformat(), "timeZone": "Europe/Paris"}, "end": {"dateTime": (date + timedelta(hours=1)).isoformat(), "timeZone": "Europe/Paris"}}
    service.events().insert(calendarId="primary", body=event).execute()
    return f"RDV cree: {title} le {date.strftime('%d/%m/%Y a %H:%M")}"

async def handle_message(update: Update, context):
    msg = update.message.text.lower()
    orig = update.message.text
    if any(w in msg for w in ["ajoute", "note", "tache", "rappelle"]):
        try:
            Client(auth=NOTION_TOKEN).blocks.children.append(block_id=NOTION_PAGE_ID, children=[{"object": "block", "type": "to_do", "to_do": {"rich_text": [{"type": "text", "text": {"content": orig}}], "checked": False}}])
            await update.message.reply_text("Tache ajoutee dans Notion.")
        except Exception as e:
            await update.message.reply_text(f"Erreur Notion: {str(e)}")
        return
    if any(w in msg for w in ["agenda", "calendrier", "evenement"]):
        try:
            await update.message.reply_text(f"Ton agenda:
{get_calendar_events()}")
        except Exception as e:
            await update.message.reply_text(f"Erreur Calendar: {str(e)}")
        return
    if any(w in msg for w in ["cree un rdv", "creer rdv", "nouveau rdv", "planifie", "programme rdv"]):
        try:
            parts = orig.split()
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            for p in parts:
                if "-" in p and len(p) == 10: date_str = p
            await update.message.reply_text(create_calendar_event(orig, date_str))
        except Exception as e:
            await update.message.reply_text(f"Erreur RDV: {str(e)}")
        return
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    response = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=1024, system="Tu es Octavius, assistant de Kamal. Direct, zero blabla. Reponds en francais. Pour creer un rdv dis: cree un rdv [titre] [YYYY-MM-DD] [HH:MM]", messages=[{"role": "user", "content": orig}])
    await update.message.reply_text(response.content[0].text)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
print('Octavius est en ligne...')
app.run_polling()
