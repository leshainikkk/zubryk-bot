from telebot import types
from zubryk import storage as db
from zubryk.config import get_mini_app_url


def home_only_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🏠 Главная", callback_data="menu"))
    return kb


def main_menu_kb():
    kb = types.InlineKeyboardMarkup()
    url=get_mini_app_url()
    if url:
        kb.add(types.InlineKeyboardButton("Открыть Зубрик", web_app=types.WebAppInfo(url), style="primary"))
    kb.add(types.InlineKeyboardButton("📚 Учить новые слова", callback_data="study"))
    kb.add(types.InlineKeyboardButton("📝 Тест по изученным словам", callback_data="test"))
    kb.add(types.InlineKeyboardButton("🎮 Играть с друзьями", callback_data="play"))
    kb.row(
        types.InlineKeyboardButton("🏆 Рейтинг", callback_data="rating"),
        types.InlineKeyboardButton("⚙️ Настройки", callback_data="settings"),
        types.InlineKeyboardButton("❓ Помощь", callback_data="help"),
    )
    return kb


def groups_kb(prefix, page=0):
    groups=db.get_groups()
    pages=max(1,(len(groups)+7)//8)
    page=max(0,min(page,pages-1))
    kb=types.InlineKeyboardMarkup()
    for group in groups[page*8:(page+1)*8]:
        kb.add(types.InlineKeyboardButton(group["name"],callback_data=f"{prefix}:{group['key']}"))
    if pages>1:
        row=[]
        if page>0:row.append(types.InlineKeyboardButton("←",callback_data=f"groups:{prefix}:{page-1}"))
        row.append(types.InlineKeyboardButton(f"{page+1} / {pages} · {len(groups)} тем",callback_data="noop"))
        if page+1<pages:row.append(types.InlineKeyboardButton("→",callback_data=f"groups:{prefix}:{page+1}"))
        kb.row(*row)
    kb.add(types.InlineKeyboardButton("Главная",callback_data="menu"))
    return kb


def daily_time_kb(back_to_settings=False):
    kb = types.InlineKeyboardMarkup()
    row = []
    for code, label in db.DAILY_TIME_CHOICES:
        row.append(types.InlineKeyboardButton(label, callback_data=f"settime:{code}"))
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    if back_to_settings:
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="settings"))
    return kb


def settings_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⏰ Изменение времени", callback_data="settings:time"))
    kb.add(types.InlineKeyboardButton("✏️ Изменить имя", callback_data="settings:name"))
    kb.add(types.InlineKeyboardButton("🆘 Поддержка", callback_data="settings:support"))
    kb.add(types.InlineKeyboardButton("🗑 Удалить профиль", callback_data="settings:delete"))
    kb.add(types.InlineKeyboardButton("🏠 Главная", callback_data="menu"))
    return kb


def rating_menu_kb():
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("🔥 За неделю", callback_data="rating:week"),
        types.InlineKeyboardButton("🥔 За всё время", callback_data="rating:all"),
    )
    kb.add(types.InlineKeyboardButton("🏠 Главная", callback_data="menu"))
    return kb


def game_groups_kb():
    return groups_kb("pg")
