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
    return "Quick Study Master Engine is Running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port)

# --- Bot Token ---
TOKEN = "8722160781:AAHqY5XPGitplUtXe0CtN0rjoPBdjt3wAFo"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 **QUICK STUDY Master Bot v3.0** Active hai!\n\n"
        "✅ **I, II, III, IV** wale statements support karta hai.\n"
        "✅ **Long Questions** khud hi Explanation mein shift ho jayenge.\n"
        "✅ **Clickable Polls** har format mein banenge."
    )

async def create_bulk_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = update.message.text
    # Question blocks split
    question_blocks = [b.strip() for b in re.split(r'\n\s*\n', raw_text.strip()) if b.strip()]
    
    total = len(question_blocks)
    if total == 0: return
    
    await update.message.reply_text(f"⚡ {total} prashn mile. Processing...")

    count = 0
    for block in question_blocks:
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if len(lines) < 2: continue

        actual_explanation = ""
        filtered_lines = []
        
        # 1. Separate Explanation
        for line in lines:
            if line.lower().startswith("ex:"):
                actual_explanation = re.sub(r'^[Ee][Xx]:\s*', '', line).strip()
            else:
                filtered_lines.append(line)

        # 2. Logic to Separate Options and Question Body
        potential_options = []
        actual_question_lines = []
        found_options = False

        # Identify options from bottom up
        for i in range(len(filtered_lines)-1, -1, -1):
            curr_line = filtered_lines[i]
            # STRICT OPTION CHECK: Checkbox (✅) or (A), (B) labels
            is_labeled = re.match(r'^[\(\[]?([a-dA-D])[\.\)\]\s-]', curr_line, re.IGNORECASE)
            has_check = "✅" in curr_line
            
            # Roman numerals (I, II, III) are NOT options
            is_roman = re.match(r'^(IX|IV|V?I{0,3})\.', curr_line, re.IGNORECASE)

            if not found_options and (is_labeled or has_check) and not is_roman:
                potential_options.insert(0, curr_line)
            elif not found_options and len(potential_options) < 4 and not is_roman and len(curr_line) < 60:
                potential_options.insert(0, curr_line)
            else:
                found_options = True
                actual_question_lines.insert(0, curr_line)

        # Build Options
        options = []
        correct_id = 0
        for opt in potential_options:
            is_correct = "✅" in opt
            clean_opt = re.sub(r'^[\(\[]?([a-dA-D1-4])[\.\)\]\s-]\s*', '', opt)
            clean_opt = clean_opt.replace("✅", "").strip()
            if clean_opt:
                options.append(clean_opt)
                if is_correct:
                    correct_id = len(options) - 1

        # 3. Handle Telegram 300 Character Limit
        full_q_text = "\n".join(actual_question_lines)
        final_explanation = actual_explanation

        if len(full_q_text) > 300:
            main_title = actual_question_lines[0]
            detailed_info = "\n".join(actual_question_lines[1:])
            full_q_text = (main_title[:290] + "...") if len(main_title) > 290 else main_title
            final_explanation = f"📋 Details:\n{detailed_info}\n\n💡 Ex: {actual_explanation}"

        # 4. Send Poll
        if 2 <= len(options) <= 10:
            while True:
                try:
                    await context.bot.send_poll(
                        chat_id=update.effective_chat.id,
                        question=full_q_text,
                        options=options[:10],
                        type=PollType.QUIZ,
                        correct_option_id=correct_id,
                        explanation=final_explanation[:200] if final_explanation else None,
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

    await update.message.reply_text(f"✅ Safaltapurvak {count} poll tayyar kiye gaye!")

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), create_bulk_quiz))
    app.run_polling()
    
