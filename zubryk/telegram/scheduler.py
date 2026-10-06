import logging
import time
from datetime import datetime
from zubryk import storage as db
from zubryk.config import TIMEZONE
from .client import bot
from .formatting import send_rich
from html import escape
from zubryk.sources import word_source

log=logging.getLogger("zubryk.scheduler")

def send_daily_words_for_time(code):
    for uid in db.get_users_due_for_daily(code):
        try:
            words = db.get_next_new_words_multi(uid, limit=5)
            if not words:
                bot.send_message(
                    uid,
                    "🏁 Ты уже изучил(а) все слова во всех темах! Загляни в «Играть с друзьями» 🎮",
                )
                db.mark_daily_sent(uid)
                continue

            lines = []
            for word_id, bel, ru in words:
                lines.append(f"<b>{escape(bel)}</b>\n{escape(ru)}")

            rich="<h2>Ваши слова на сегодня</h2>"+"".join(f"<p><b>{escape(bel)}</b><br>{escape(ru)}</p>" for _,bel,ru in words)
            fallback="<b>Ваши слова на сегодня</b>\n\n"+"\n\n".join(lines)
            credited=[word_source(bel) for _,bel,_ in words]
            if any(credited):
                credit=' · '.join(f'<a href="{escape(source["url"],quote=True)}">{index+1}</a>' for index,source in enumerate(credited) if source)
                footer=f'Викисловарь: {credit} · <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>'
                rich+=f"<p>{footer}</p>"
                fallback+="\n\n"+footer
            send_rich(bot,uid,rich,fallback)
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
