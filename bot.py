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
        "🚀 **QUICK STUDY Master Bot v2.0** अपडेट हो गया है!\n\n"
        "✅ अब बहुत लंबे प्रश्न भी बिना कटे बनेंगे।\n"
        "✅ अगर प्रश्न 300 शब्दों से बड़ा होगा, तो बाकी जानकारी 'Explanation' में आ जाएगी।"
    )

async def create_bulk_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = update.message.text
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
        explanation_body = ""
        
        # 1. Explanation को अलग करना
        filtered_lines = []
        for line in lines:
            if line.lower().startswith("ex:"):
                explanation_body = re.sub(r'^[Ee][Xx]:\s*', '', line).strip()
            else:
                filtered_lines.append(line)

        # 2. विकल्प और प्रश्न को अलग करना
        potential_options = []
        actual_question_lines = []
        found_options = False

        for i in range(len(filtered_lines)-1, -1, -1):
            curr_line = filtered_lines[i]
            # विकल्प की पहचान: (A) या ✅ या छोटी लाइन
            is_labeled = re.match(r'^[\(\[]?([a-dA-D1-4])[\.\)\]\s-]', curr_line)
            has_check = "✅" in curr_line
            
            if not found_options and (is_labeled or has_check or len(potential_options) < 4):
                if len(curr_line) > 100 and not has_check:
                    actual_question_lines.insert(0, curr_line)
                    found_options = True
                else:
                    potential_options.insert(0, curr_line)
            else:
                found_options = True
                actual_question_lines.insert(0, curr_line)

        # विकल्पों को साफ़ करना
        for opt in potential_options:
            is_correct = "✅" in opt
            clean_opt = re.sub(r'^[\(\[]?([a-dA-D1-4])[\.\)\]\s-]\s*', '', opt)
            clean_opt = clean_opt.replace("✅", "").strip()
            if clean_opt:
                options.append(clean_opt)
                if is_correct:
                    correct_id = len(options) - 1

        # 3. प्रश्न की लंबाई मैनेज करना (Telegram Limit: 300)
        full_q_text = "\n".join(actual_question_lines)
        final_explanation = explanation_body

        if len(full_q_text) > 300:
            # अगर प्रश्न बड़ा है, तो मुख्य प्रश्न को ऊपर रखें और कथनों को Explanation में डालें
            title = actual_question_lines[0]
            statements = "\n".join(actual_question_lines[1:])
            full_q_text = title[:295] + "..."
            final_explanation = f"📋 प्रश्न विवरण:\n{statements}\n\n💡 व्याख्या: {explanation_body}"

        # 4. पोल भेजना
        if 2 <= len(options) <= 10:
            while True:
                try:
                    await context.bot.send_poll(
                        chat_id=update.effective_chat.id,
                        question=full_q_text,
                        options=options[:10],
                        type=PollType.QUIZ,
                        correct_option_id=correct_id,
                        explanation=final_explanation[:200], # Explanation Limit: 200
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
    
