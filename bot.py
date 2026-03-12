import logging
import re
import asyncio
import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import PollType
from telegram.error import RetryAfter

# Logging Setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- Render Flask Server ---
flask_app = Flask(__name__)
@flask_app.route('/')
def health_check():
    return "Bot is Running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port)

# --- Telegram Bot Logic ---
TOKEN = "8753514994:AAGbwCwus8v7KBeNHN6tXW2cZIE7vLXXCX8"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 **Universal Bot (Fixed)** तैयार है!\n\nअब (A), (B), (C), (D) वाले विकल्प सही से Clickable बनेंगे।")

async def create_bulk_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = update.message.text
    question_blocks = [b.strip() for b in re.split(r'\n\s*\n', raw_text.strip()) if b.strip()]
    
    total = len(question_blocks)
    if total == 0: return
    
    await update.message.reply_text(f"⚡ {total} प्रश्न मिले। प्रोसेसिंग शुरू...")

    count = 0
    for block in question_blocks:
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if len(lines) < 2: continue

        question_parts = []
        options = []
        correct_id = 0
        explanation = ""
        option_detected = False

        for line in lines:
            # 1. Explanation (Ex:) - पूरा टेक्स्ट उठाना
            if line.lower().startswith("ex:"):
                explanation = re.sub(r'^[Ee][Xx]:\s*', '', line).strip()
                continue

            # 2. विकल्पों की पहचान - केवल तभी जब लाइन (A), A., (1) या 1. से शुरू हो
            # और उसके बाद कोई विकल्प हो। यह '1. यदि लेंस...' जैसे लंबे प्रश्न को नहीं पकड़ेगा।
            # हमने Regex को 'A-D' के लिए सख्त कर दिया है ताकि clickable बटन सही बनें।
            option_match = re.match(r'^[\(\[]?([a-dA-D])[\.\)\]\s-]\s*(.*)', line, re.IGNORECASE)
            
            if option_match:
                option_detected = True
                opt_text = option_match.group(2).strip()
                is_correct = "✅" in line
                clean_opt = opt_text.replace("✅", "").strip()
                
                if clean_opt:
                    options.append(clean_opt)
                    if is_correct:
                        correct_id = len(options) - 1
                continue

            # 3. प्रश्न का हिस्सा (जब तक विकल्प न मिलें)
            if not option_detected:
                question_parts.append(line)

        full_question = "\n".join(question_parts)

        if 2 <= len(options) <= 10:
            while True:
                try:
                    await context.bot.send_poll(
                        chat_id=update.effective_chat.id,
                        question=full_question[:300],
                        options=options[:10],
                        type=PollType.QUIZ,
                        correct_option_id=correct_id,
                        explanation=explanation[:200] if explanation else None,
                        is_anonymous=False
                    )
                    count += 1
                    await asyncio.sleep(0.5) 
                    break 
                except RetryAfter as e:
                    await asyncio.sleep(e.retry_after)
                except Exception as e:
                    logging.error(f"Error: {e}")
                    break

    await update.message.reply_text(f"✅ सफलतापूर्वक {count} पोल तैयार किए गए!")

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), create_bulk_quiz))
    app.run_polling()
    
