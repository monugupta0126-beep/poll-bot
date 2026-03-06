import logging
import re
import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import PollType
from flask import Flask
from threading import Thread

# --- Flask Server for Render ---
app = Flask('')

@app.route('/')
def home():
    return "QUICK STUDY Bot is Running Live!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- Bot Config ---
TOKEN = "8753514994:AAGbwCwus8v7KBeNHN6tXW2cZIE7vLXXCX8"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 **QUICK STUDY Permanent Bot** Live!\nप्रश्नों का सेट भेजें।")

async def create_bulk_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = update.message.text
    question_blocks = re.split(r'\n\s*\n', raw_text.strip())
    
    for block in question_blocks:
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if len(lines) < 2: continue

        question = lines[0]
        options = []
        correct_id = 0
        explanation = ""

        for line in lines[1:]:
            if line.upper().startswith("EX:"):
                exp_clean = re.split(r'𝐉𝐎इ𝐍', line, flags=re.IGNORECASE)[0]
                explanation = exp_clean.replace("Ex:", "").replace("EX:", "").strip()
                continue
            
            if "JOIN" in line.upper() or "@" in line:
                continue

            is_correct = "✅" in line
            clean_option = line.replace("✅", "").strip()
            clean_option = re.sub(r'^[a-zA-Z0-9][\.\)]\s*', '', clean_option)

            if clean_option:
                options.append(clean_option)
                if is_correct:
                    correct_id = len(options) - 1

        if len(options) >= 2:
            try:
                await context.bot.send_poll(
                    chat_id=update.effective_chat.id,
                    question=question[:300],
                    options=options[:10],
                    type=PollType.QUIZ,
                    correct_option_id=correct_id,
                    explanation=explanation[:200] if explanation else None,
                    is_anonymous=False
                )
                await asyncio.sleep(0.6) 
            except Exception:
                continue

if __name__ == '__main__':
    Thread(target=run_web).start()
    bot_app = ApplicationBuilder().token(TOKEN).read_timeout(120).write_timeout(120).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), create_bulk_quiz))
    print("Bot is starting...")
    bot_app.run_polling()
