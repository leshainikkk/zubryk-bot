from html import escape

from zubryk import storage as db
from . import cards
from .client import bot
from .formatting import send_html, send_rich
from .keyboards import main_menu_kb, settings_kb, home_only_kb


def main_menu_text(uid):
    return cards.main_menu_text(db.get_or_create_user(uid))


def show_main_menu(chat_id, *, message=None):
    user = db.get_or_create_user(chat_id)
    return send_rich(
        bot, chat_id, cards.main_menu_rich(user), cards.main_menu_text(user),
        main_menu_kb(), message=message,
    )


def send_screen(chat_id, text, kb=None, *, message=None):
    return send_html(bot, chat_id, text, kb, message=message)


def show_settings_menu(chat_id, *, message=None, notice=None):
    user = db.get_or_create_user(chat_id)
    return send_screen(
        chat_id, cards.settings_text(user, db.daily_time_label(user['daily_time']), notice=notice),
        settings_kb(), message=message,
    )


def show_help(chat_id, *, message=None):
    return send_rich(
        bot, chat_id, cards.HELP_RICH, cards.HELP_TEXT,
        home_only_kb(), message=message,
    )


def format_rating(top, me):
    medals = {1: '🥇', 2: '🥈', 3: '🥉'}
    lines = []
    for uid, name, amount, rank in top:
        prefix = medals.get(rank, f'{rank}.')
        label = escape(name or 'Без имени')
        if me and uid == me[0]:
            label = f'<b>{label} · ты</b>'
        lines.append(f'{prefix} {label} — <b>{cards.number(amount)}</b> 🥔')
    if not lines:
        lines.append('Пока здесь пусто. Сыграй с другом, чтобы попасть в рейтинг.')
    if me and not any(row[0] == me[0] for row in top):
        lines.append(f'\n<blockquote>Твоё место: <b>{me[3]}</b> · <b>{cards.number(me[2])}</b> 🥔</blockquote>')
    return '\n'.join(lines)
