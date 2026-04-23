import anthropic
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from notion_client import Client
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_PAGE_ID = os.environ.get("NOTION_PAGE_ID")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = os.environ.get("GOOGLE_REFRESH_TOKEN")

def get_calendar_events():
    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET
    )
    service = build("calendar", "v3", credentials=creds)
    now = datetime.utcnow().isoformat() + "Z"
    end = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
    events_result = service.events().list(
        calendarId="primary", timeMin=now, timeMax=end,
        maxResults=5, singleEvents=True, orderBy="startTime"
    ).execute()
    events = events_result.get("items", [])
    if not events:
        return "Aucun evenement aujourd hui."
    result = ""
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        result += f"- {event['summary']} a {start}\n"
    return result

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    if any(word in user_message.lower() for word in ["ajoute", "note", "tache", "rappelle"]):
        try:
            notion = Client(auth=NOTION_TOKEN)
            notion.blocks.children.append(
                block_id=NOTION_PAGE_ID,
                children=[{
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"type": "text", "text": {"content": user_message}}],
                        "checked": False
                    }
                }]
            )
            await update.message.reply_text("Tache ajoutee dans Notion.")
            return
        except Exception as e:
            await update.message.reply_text(f"Erreur Notion: {str(e)}")
            return

    if any(word in user_message.lower() for word in ["agenda", "calendrier", "rendez-vous", "evenement"]):
        try:
            events = get_calendar_events()
            await update.message.reply_text(f"Ton agenda aujourd hui:\n{events}")
            return
        except Exception as e:
            await update.message.reply_text(f"Erreur Calendar: {str(e)}")
            return

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system="Tu es Octavius, l assistant personnel de Kamal. Tu es direct, zero blabla, oriente action. Reponds en francais.",
        messages=[{"role": "user", "content": user_message}]
    )
    await update.message.reply_text(response.content[0].text)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
print("Octavius est en ligne...")
app.run_polling()
