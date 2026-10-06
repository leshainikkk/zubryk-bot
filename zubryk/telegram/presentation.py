from html import escape
from .formatting import send_rich
from zubryk import storage as db
from .client import bot
from .keyboards import *

HELP_TEXT = (
    "ℹ️ *Как всё устроено*\n\n"
    "📚 *Учить новые слова* — выбери тему, слова показываются по одному, "
    "кнопка «Дальше» открывает следующее.\n"
    "📝 *Тест* — бот спрашивает перевод слов, которые ты уже изучил(а). "
    "Пока не изучишь ни одного слова, тест недоступен.\n"
    "🥔 *Бульба* — внутренняя валюта. Начисляется за игру с друзьями "
    "и участвует в рейтинге.\n"
    "🔥 *Стрик* — число дней подряд с занятиями. Пропустишь день целиком — "
    "серия начнётся заново с 1.\n"
    "🎮 *Играть с друзьями* — выбери тему, отправь другу ссылку-приглашение. "
    "Как только он перейдёт по ней — начнётся игра 1 на 1: на каждый раунд "
    "4 варианта перевода, кто ошибся первым — проиграл, а победитель получает "
    "дополнительно +30🥔.\n"
    "⚙️ *Настройки* — время ежедневных слов, имя, поддержка, удаление профиля.\n"
    "🏆 *Рейтинг* — топ игроков за неделю и за всё время."
)

def main_menu_text(uid):
    user = db.get_or_create_user(uid)
    name = escape(user["name"] or "Друг")
    return f"<b>Прывітанне, {name}!</b>\n\n{user['balance']} 🥔 · {user['streak']} 🔥\n\nСлова и игры — в чате. Грамматика и ваш прогресс — в приложении."


def show_main_menu(chat_id):
    user = db.get_or_create_user(chat_id)
    name = escape(user["name"] or "Друг")
    rich = f"<h2>Прывітанне, {name}!</h2><p><b>{user['balance']} 🥔</b> · <b>{user['streak']} 🔥</b></p><p>Слова и игры — в чате. Грамматика и ваш прогресс — в приложении.</p>"
    return send_rich(bot, chat_id, rich, main_menu_text(chat_id), main_menu_kb())


def send_screen(chat_id, text, kb, parse_mode=None):
    bot.send_message(chat_id, text, reply_markup=kb, parse_mode=parse_mode)


def show_settings_menu(chat_id):
    bot.send_message(chat_id, "⚙️ Настройки", reply_markup=settings_kb())


def format_rating(top, me):
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    if not top:
        lines = ["Пока в рейтинге никого нет."]
    else:
        lines = []
        for uid_, name, amount, rank in top:
            prefix = medals.get(rank, f"{rank}.")
            lines.append(f"{prefix} {escape(name or 'Без имени')} — {amount}🥔")
    if me and (not top or me[3] > top[-1][3]):
        lines.append("")
        lines.append(f"Ты: {me[3]} место — {me[2]}🥔")
    return "\n".join(lines)
