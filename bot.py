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

# --- Render Flask Server (For 24/7 Online) ---
flask_app = Flask(__name__)
@flask_app.route('/')
def health_check():
    return "QUICK STUDY Universal Bot is Ready!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port)

# --- आपका बोट टोकन ---
TOKEN = "8722160781:AAHqY5XPGitplUtXe0CtN0rjoPBdjt3wAFo"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 **QUICK STUDY Universal Engine** लोड हो गया है!\n\n"
        "अब आप दुनिया का कोई भी प्रश्न इन 3 फॉर्मेट में भेजें:\n"
        "1️⃣ **Simple MCQ** (A, B, C, D)\n"
        "2️⃣ **Statement Based** (1, 2, 3 कथन वाले)\n"
        "3️⃣ **Assertion-Reason** (कथन और कारण वाले)\n\n"
        "बोट खुद ही उन्हें पहचान कर बल्क में पोल बना देगा।"
    )

async def create_bulk_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = update.message.text
    # प्रश्नों के ब्लॉक्स को अलग करना (Double newline)
    question_blocks = [b.strip() for b in re.split(r'\n\s*\n', raw_text.strip()) if b.strip()]
    
    total = len(question_blocks)
    if total == 0: return
    
    await update.message.reply_text(f"⚡ {total} प्रश्न मिले। बल्क प्रोसेसिंग शुरू...")

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
            # 1. Explanation (Ex:) - पूरा टेक्स्ट (लिंक सहित) उठाना
            if line.lower().startswith("ex:"):
                explanation = re.sub(r'^[Ee][Xx]:\s*', '', line).strip()
                continue

            # 2. विकल्पों की सख्त पहचान (केवल A-D बटन बनेंगे)
            # यह 1. 2. 3. को प्रश्न के अंदर ही रहने देगा
            match_option = re.match(r'^[\(\[]?([a-dA-D])[\.\)\]\s-]\s*(.*)', line, re.IGNORECASE)
            
            # अगर ऊपर वाला मैच न हो, तो भी चेक करें कि क्या लाइन बिना ब्रैकेट के A/B/C/D से शुरू है (Simple format के लिए)
            if not match_option:
                match_option = re.match(r'^([A-Da-d])\s+(.*)', line)

            if match_option:
                option_detected = True
                option_text = match_option.group(2).strip()
                is_correct = "✅" in line
                clean_opt = option_text.replace("✅", "").strip()
                
                if clean_opt:
                    options.append(clean_opt)
                    if is_correct:
                        correct_id = len(options) - 1
                continue

            # 3. जब तक विकल्प नहीं मिलते, सब कुछ प्रश्न का हिस्सा है
            if not option_detected:
                question_parts.append(line)

        full_question = "\n".join(question_parts)

        # पोल भेजना
        if 2 <= len(options) <= 10:
            while True:
                try:
                    await context.bot.send_poll(
                        chat_id=update.effective_chat.id,
                        question=full_question[:300], # 300 char limit
                        options=options[:10],
                        type=PollType.QUIZ,
                        correct_option_id=correct_id,
                        explanation=explanation[:200] if explanation else None, # 200 char limit
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
