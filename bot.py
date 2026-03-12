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
    return "Quick Study Universal Engine is Running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port)

# --- Bot Token ---
TOKEN = "8722160781:AAHqY5XPGitplUtXe0CtN0rjoPBdjt3wAFo"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 **QUICK STUDY Master Bot** एक्टिव है!\n\n"
        "आप इन 3 में से किसी भी फॉर्मेट में प्रश्न भेजें:\n"
        "1️⃣ **Simple** (बिना A, B, C, D के भी चलेगा)\n"
        "2️⃣ **Statements** (1, 2, 3 कथन वाले)\n"
        "3️⃣ **Assertion-Reason** (कथन-कारण वाले)\n\n"
        "बल्क में हज़ारों प्रश्न प्रोसेस करने के लिए तैयार।"
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
        
        # पहले हम Explanation को अलग कर लेते हैं
        temp_lines = []
        for line in lines:
            if line.lower().startswith("ex:"):
                explanation = re.sub(r'^[Ee][Xx]:\s*', '', line).strip()
            else:
                temp_lines.append(line)

        # अब विकल्प और प्रश्न को अलग करने का उन्नत तरीका
        # हम नीचे से ऊपर की तरफ चेक करेंगे कि विकल्प कहाँ खत्म हो रहे हैं
        found_options = False
        potential_options = []
        actual_question = []

        # अगर आखिरी 4 लाइनों में ✅ है या वे छोटी हैं, तो वे विकल्प हैं
        for i in range(len(temp_lines)-1, -1, -1):
            curr_line = temp_lines[i]
            
            # अगर विकल्प (A), (B) से शुरू हो रहे हैं
            is_labeled = re.match(r'^[\(\[]?([a-dA-D1-4])[\.\)\]\s-]', curr_line)
            # या अगर उनमें ✅ लगा है
            has_check = "✅" in curr_line
            
            if (is_labeled or has_check or (len(potential_options) < 4 and not found_options)):
                # यह लाइन एक विकल्प हो सकती है
                # लेकिन अगर ये '1. यदि...' जैसा बड़ा कथन है, तो इसे प्रश्न में ही रहने दें
                if len(curr_line) > 100 and not has_check:
                    actual_question.insert(0, curr_line)
                    found_options = True # अब इसके ऊपर सब प्रश्न है
                else:
                    potential_options.insert(0, curr_line)
            else:
                found_options = True
                actual_question.insert(0, curr_line)

        # विकल्पों को साफ़ करना
        for idx, opt in enumerate(potential_options):
            is_correct = "✅" in opt
            # टिक और लेबल (A., B.) हटाना
            clean_opt = re.sub(r'^[\(\[]?([a-dA-D1-4])[\.\)\]\s-]\s*', '', opt)
            clean_opt = clean_opt.replace("✅", "").strip()
            
            if clean_opt:
                options.append(clean_opt)
                if is_correct:
                    correct_id = len(options) - 1

        full_question = "\n".join(actual_question)

        # पोल भेजना
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
