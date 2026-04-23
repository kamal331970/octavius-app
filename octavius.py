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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    low = msg.lower()

    if any(w in low for w in ["ajoute", "note", "tache", "rappelle"]):
        try:
            Client(auth=NOTION_TOKEN).blocks.children.append(
                block_id=NOTION_PAGE_ID,
                children=[{
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"type": "text", "text": {"content": msg}}],
                        "checked": False
                    }
                }]
            )
            await update.message.reply_text("Tache ajoutee dans Notion.")
        except Exception as e:
            await update.message.reply_text("Erreur Notion: " + str(e))
        return

    if any(w in low for w in ["agenda", "calendrier", "evenement"]):
        try:
            await update.message.reply_text("Ton agenda:\n" + get_events())
        except Exception as e:
            await update.message.reply_text("Erreur Calendar: " + str(e))
        return

    if any(w in low for w in ["cree un rdv", "creer rdv", "nouveau rdv", "planifie", "programme rdv"]):
        try:
            parts = msg.split()
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            time_str = "10:00"
            for p in parts:
                if "-" in p and len(p) == 10:
                    date_str = p
                if ":" in p and len(p) == 5:
                    time_str = p
            await update.message.reply_text(make_event(msg, date_str, time_str))
        except Exception as e:
            await update.message.reply_text("Erreur RDV: " + str(e))
        return

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    r = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system="Tu es Octavius, assistant de Kamal. Direct, zero blabla. Reponds en francais.",
        messages=[{"role": "user", "content": msg}]
    )
    await update.message.reply_text(r.content[0].text)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
print("Octavius est en ligne...")
app.run_polling()
