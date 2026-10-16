import logging
import time
from datetime import datetime
from zubryk import storage as db
from zubryk.config import TIMEZONE
from .client import bot
from .formatting import send_rich
from .cards import daily_words_card
from .keyboards import daily_words_kb, home_only_kb
from .formatting import send_html

log=logging.getLogger("zubryk.scheduler")

def send_daily_words_for_time(code):
    for uid in db.get_users_due_for_daily(code):
        try:
            words = db.get_next_new_words_multi(uid, limit=5)
            if not words:
                send_html(bot,
                    uid,
                    "🏁 <b>Весь словарь пройден!</b>\n\nПовтори изученное в тесте или сыграй с другом.",
                    home_only_kb(),
                )
                db.mark_daily_sent(uid)
                continue

            rich, fallback = daily_words_card(words)
            send_rich(bot, uid, rich, fallback, daily_words_kb())
            for word_id,_,_ in words:
                db.mark_word_learned(uid,word_id)
            db.mark_daily_sent(uid)
        except Exception:
            log.exception("Failed to send daily words to user %s", uid)

def loop():
    choices=dict(db.DAILY_TIME_CHOICES)
    last_minute=None
    while True:
        now=datetime.now(TIMEZONE)
        minute=now.strftime("%Y-%m-%d %H:%M")
        code=now.strftime("%H%M")
        if minute != last_minute and code in choices:
            send_daily_words_for_time(code)
            last_minute=minute
        time.sleep(10)
