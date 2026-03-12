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

# --- Render Flask Server (बोट को 24/7 चालू रखने के लिए) ---
flask_app = Flask(__name__)
@flask_app.route('/')
def health_check():
    return "QUICK STUDY Universal Bot is Live!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port)

# --- आपका बोट टोकन ---
TOKEN = "8753514994:AAGbwCwus8v7KBeNHN6tXW2cZIE7vLXXCX8"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 **QUICK STUDY Universal Bot** पूरी तरह तैयार है!\n\n"
        "✅ **Simple MCQ**\n"
        "✅ **Statement 1, 2, 3**\n"
        "✅ **Assertion-Reason (कथन-कारण)**\n\n"
        "आप 50-60 प्रश्न बल्क में भेजें, मैं सबका सही पोल बना दूँगा।"
    )

async def create_bulk_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = update.message.text
    # प्रश्नों के ब्लॉक्स को अलग करना (Double newline)
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
            # 1. Explanation (Ex:) पहचानना - अब यह कुछ भी नहीं काटेगा (FULL TEXT)
            if line.lower().startswith("ex:"):
                # "Ex:" को हटाकर बाकी पूरा टेक्स्ट (लिंक सहित) उठाना
                explanation = re.sub(r'^[Ee][Xx]:\s*', '', line).strip()
                continue

            # 2. विकल्पों की पहचान - (A), (B), (C), (D) फॉर्मेट के लिए सख्त Regex
            # यह सुनिश्चित करता है कि कथन 1, 2, 3 गलती से विकल्प न बन जाएँ
            match_option = re.match(r'^[\(\[]?([a-dA-D])[\.\)\]\s-]\s*(.*)', line, re.IGNORECASE)
            
            if match_option:
                option_detected = True
                option_text = match_option.group(2).strip()
                is_correct = "✅" in line
                
                # टिक मार्क हटाकर बटन के लिए साफ़ टेक्स्ट
                clean_opt = option_text.replace("✅", "").strip()
                
                if clean_opt:
                    options.append(clean_opt)
                    if is_correct:
                        correct_id = len(options) - 1
                continue

            # 3. प्रश्न का हिस्सा (जब तक विकल्प न मिलें)
            if not option_detected:
                question_parts.append(line)

        # पूरे प्रश्न को जोड़ना
        full_question = "\n".join(question_parts)

        # पोल भेजने की प्रक्रिया (Flood protection के साथ)
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
    # Render के लिए Flask थ्रेड
    threading.Thread(target=run_flask, daemon=True).start()
    
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), create_bulk_quiz))
    
    print("Universal Bot is running...")
    app.run_polling()
    
