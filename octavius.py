import anthropic
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from notion_client import Client

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_PAGE_ID = os.environ.get("NOTION_PAGE_ID")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    # Ajouter tache dans Notion si demande
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
    
    # Reponse Claude par defaut
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
