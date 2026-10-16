from telebot import types
from zubryk import storage as db
from zubryk.config import get_mini_app_url
from urllib.parse import urlencode

TOPICS_PER_PAGE = 8


def home_only_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🏠 Главная", callback_data="menu"))
    return kb


def main_menu_kb():
    kb = types.InlineKeyboardMarkup()
    url=get_mini_app_url()
    if url:
        kb.add(types.InlineKeyboardButton("🌿 Открыть приложение", web_app=types.WebAppInfo(url)))
    kb.add(types.InlineKeyboardButton("📚 Новые слова", callback_data="study", style="primary"))
    kb.row(
        types.InlineKeyboardButton("📝 Проверить себя", callback_data="test"),
        types.InlineKeyboardButton("🎮 Игра с другом", callback_data="play"),
    )
    kb.row(
        types.InlineKeyboardButton("🏆 Рейтинг", callback_data="rating"),
        types.InlineKeyboardButton("⚙️ Настройки", callback_data="settings"),
    )
    kb.add(types.InlineKeyboardButton("Как заниматься?", callback_data="help"))
    return kb


def groups_kb(prefix, page=0):
    groups=db.get_groups()
    pages=max(1,(len(groups)+TOPICS_PER_PAGE-1)//TOPICS_PER_PAGE)
    page=max(0,min(page,pages-1))
    kb=types.InlineKeyboardMarkup()
    for group in groups[page*TOPICS_PER_PAGE:(page+1)*TOPICS_PER_PAGE]:
        kb.add(types.InlineKeyboardButton(group["name"],callback_data=f"{prefix}:{group['key']}"))
    if pages>1:
        row=[]
        if page>0:row.append(types.InlineKeyboardButton("‹ Назад",callback_data=f"groups:{prefix}:{page-1}"))
        row.append(types.InlineKeyboardButton(f"{page+1} / {pages}",callback_data="noop"))
        if page+1<pages:row.append(types.InlineKeyboardButton("Далее ›",callback_data=f"groups:{prefix}:{page+1}"))
        kb.row(*row)
    kb.add(types.InlineKeyboardButton("🏠 Главная",callback_data="menu"))
    return kb


def daily_time_kb(back_to_settings=False, *, selected=None):
    kb = types.InlineKeyboardMarkup()
    row = []
    for code, label in db.DAILY_TIME_CHOICES:
        if code == "off":
            continue
        active = code == selected
        row.append(types.InlineKeyboardButton(
            ("✓ " if active else "") + label, callback_data=f"settime:{code}",
            style="success" if active else None,
        ))
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    off_active = back_to_settings and selected is None
    kb.add(types.InlineKeyboardButton(
        "✓ Не присылать" if off_active else "Не присылать",
        callback_data="settime:off", style="success" if off_active else None,
    ))
    if back_to_settings:
        kb.add(types.InlineKeyboardButton("‹ Настройки", callback_data="settings"))
    return kb


def settings_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⏰ Время слов дня", callback_data="settings:time"))
    kb.add(types.InlineKeyboardButton("✏️ Изменить имя", callback_data="settings:name"))
    kb.add(types.InlineKeyboardButton("🆘 Поддержка", callback_data="settings:support"))
    kb.add(types.InlineKeyboardButton("🗑 Удалить профиль", callback_data="settings:delete", style="danger"))
    kb.add(types.InlineKeyboardButton("🏠 Главная", callback_data="menu"))
    return kb


def rating_menu_kb(selected=None):
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("За неделю", callback_data="rating:week", style="primary" if selected == "week" else None),
        types.InlineKeyboardButton("За всё время", callback_data="rating:all", style="primary" if selected == "all" else None),
    )
    kb.add(types.InlineKeyboardButton("🏠 Главная", callback_data="menu"))
    return kb


def game_groups_kb():
    return groups_kb("pg")


def study_word_kb(group_key):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Следующее слово →", callback_data=f"sg:{group_key}", style="primary"))
    kb.row(
        types.InlineKeyboardButton("‹ Темы", callback_data="study"),
        types.InlineKeyboardButton("🏠 Главная", callback_data="menu"),
    )
    return kb


def test_result_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📝 Повторить ещё раз", callback_data="test", style="primary"))
    kb.row(
        types.InlineKeyboardButton("📚 Новые слова", callback_data="study"),
        types.InlineKeyboardButton("🏠 Главная", callback_data="menu"),
    )
    return kb


def invitation_kb(link):
    kb = types.InlineKeyboardMarkup()
    share = "https://t.me/share/url?" + urlencode({"url": link, "text": "Сыграем в Зубрыка? 🎮"})
    kb.add(types.InlineKeyboardButton("Отправить другу ↗", url=share, style="primary"))
    kb.add(types.InlineKeyboardButton("Скопировать ссылку", copy_text=types.CopyTextButton(link)))
    kb.row(
        types.InlineKeyboardButton("‹ Темы игры", callback_data="play"),
        types.InlineKeyboardButton("🏠 Главная", callback_data="menu"),
    )
    return kb


def daily_words_kb():
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("📝 Проверить себя", callback_data="test", style="primary"),
        types.InlineKeyboardButton("📚 Ещё слова", callback_data="study"),
    )
    kb.add(types.InlineKeyboardButton("🏠 Главная", callback_data="menu"))
    return kb
