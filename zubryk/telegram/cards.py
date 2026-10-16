"""Chat copy and Telegram HTML, shared by handlers and the daily digest."""

from datetime import datetime, timedelta
from html import escape

from zubryk.config import TIMEZONE
from zubryk.sources import word_source


def number(value):
    return f"{value:,}".replace(",", " ")


def plural(value, forms):
    value = abs(value) % 100
    if 11 <= value <= 14:
        return forms[2]
    if value % 10 == 1:
        return forms[0]
    if 2 <= value % 10 <= 4:
        return forms[1]
    return forms[2]


def current_streak(user):
    last = user.get("last_activity_date")
    yesterday = datetime.now(TIMEZONE).date() - timedelta(days=1)
    return (user.get("streak") or 0) if last and last >= yesterday else 0


def main_menu_text(user):
    name = escape(user.get("name") or "Друг")
    streak = current_streak(user)
    return (
        f"<b>Прывітанне, {name}!</b>\n"
        "Твоя беларуская — каждый день.\n\n"
        f"<blockquote>🔥 <b>{streak}</b> {plural(streak, ('день', 'дня', 'дней'))} подряд"
        f"   ·   🥔 <b>{number(user.get('balance') or 0)}</b> бульбы</blockquote>\n"
        "Открой новое слово, проверь себя или сыграй с другом.\n\n"
        "<i>В приложении — прогресс, грамматика и подготовка к ЦТ / ЦЭ.</i>"
    )


def main_menu_rich(user):
    name = escape(user.get("name") or "Друг")
    streak = current_streak(user)
    return (
        f"<h2>Прывітанне, {name}!</h2>"
        "<p>Твоя беларуская — каждый день.</p>"
        f"<blockquote>🔥 <b>{streak}</b> {plural(streak, ('день', 'дня', 'дней'))} подряд"
        f" · 🥔 <b>{number(user.get('balance') or 0)}</b> бульбы</blockquote>"
        "<p>Открой новое слово, проверь себя или сыграй с другом.</p>"
        "<footer>В приложении — прогресс, грамматика и подготовка к ЦТ / ЦЭ.</footer>"
    )


def source_footer(bel):
    source = word_source(bel)
    if not source:
        return ""
    return (
        f'<i><a href="{escape(source["url"], quote=True)}">Викисловарь</a>'
        f' · <a href="{escape(source["licenseUrl"], quote=True)}">CC BY-SA 4.0</a></i>'
    )


def study_word_text(bel, ru, topic):
    text = (
        f"📚 <b>Новое слово</b>\n<i>{escape(topic)}</i>\n\n"
        f"<blockquote><b>{escape(bel)}</b></blockquote>\n"
        f"Перевод: <tg-spoiler>{escape(ru)}</tg-spoiler>\n\n"
        "<i>Нажми на скрытый перевод, чтобы проверить себя.</i>"
    )
    footer = source_footer(bel)
    return text + ("\n\n" + footer if footer else "")


def topics_text(for_game=False):
    if for_game:
        return (
            "🎮 <b>Игра с другом</b>\n\nВыбери тему для дуэли. "
            "Затем отправь другу приглашение.\n\n"
            "<blockquote>4 варианта перевода · до первой ошибки\n"
            "Верный ответ: +1 🥔 · победа: ещё +30 🥔</blockquote>"
        )
    return (
        "📚 <b>Что изучим сегодня?</b>\n\n"
        "Выбери тему — будем открывать слова по одному.\n\n"
        "<i>Перевод скрыт: сначала попробуй вспомнить его сам.</i>"
    )


def settings_text(user, daily_label, *, notice=None):
    name = escape(user.get("name") or "Друг")
    time = escape(daily_label.replace("❌ ", ""))
    text = (
        "⚙️ <b>Твои настройки</b>\n\n"
        f"Имя: <b>{name}</b>\nСлова дня: <b>{time}</b>\n"
        f"Часовой пояс: <b>{escape(str(TIMEZONE))}</b>\n\n"
        "<i>Выбери, что хочешь изменить.</i>"
    )
    return (f"✅ {escape(notice)}\n\n" if notice else "") + text


def time_text(*, onboarding=False):
    title = "Когда будем заниматься?" if onboarding else "Время для слов"
    return (
        f"⏰ <b>{title}</b>\n\nКаждый день — 5 новых слов "
        "прямо в этот чат. Выбери удобное время.\n\n"
        f"<i>Часовой пояс: {escape(str(TIMEZONE))}. Рассылку можно отключить.</i>"
    )


def test_question_text(ru, index, total, feedback=None):
    progress = f"Вопрос {index} из {total}" if total else "Повторение"
    text = (
        f"📝 <b>Проверим себя</b>\n<i>{progress}</i>\n\n"
        "Как будет по-белорусски?\n"
        f"<blockquote><b>{escape(ru)}</b></blockquote>\n"
        "<i>Напиши перевод сообщением.</i>"
    )
    return (feedback + "\n\n" if feedback else "") + text


def test_feedback_text(correct, bel):
    if correct:
        return f"✅ <b>Правильно!</b> {escape(bel)}"
    return f"✍️ <b>Запомним:</b> правильный ответ — <b>{escape(bel)}</b>."


def test_result_text(correct, completed, feedback=None):
    title = "Без ошибок. Выдатна!" if completed and correct == completed else "Хорошая тренировка!"
    score = f"<blockquote>✅ Верно: <b>{correct} из {completed}</b></blockquote>\n\n" if completed else ""
    text = (
        f"🏁 <b>Тест завершён</b>\n\n{score}{title}\n"
        "Можно повторить ещё раз или открыть новые слова."
    )
    return (feedback + "\n\n" if feedback else "") + text


def game_round_text(word, round_number):
    return (
        f"🎮 <b>Дуэль</b> · раунд {round_number}\n\n"
        "Как переводится это слово?\n"
        f"<blockquote><b>{escape(word)}</b></blockquote>\n"
        "<i>Выбери один из четырёх вариантов.</i>"
    )


def invitation_text(topic, link):
    return (
        f"🎮 <b>Дуэль готова</b>\n<i>{escape(topic)}</i>\n\n"
        "Отправь приглашение другу. Игра начнётся, когда он подключится.\n\n"
        f'<a href="{escape(link, quote=True)}">Приглашение в игру</a>\n\n'
        "<blockquote>Верный ответ: +1 🥔\nПобеда: ещё +30 🥔</blockquote>"
    )


def daily_words_card(words):
    fallback = ["☀️ <b>Слова на сегодня</b>", "Попробуй вспомнить перевод, затем нажми на него."]
    rich = ["<h2>☀️ Слова на сегодня</h2>", "<p>Попробуй вспомнить перевод, затем нажми на него.</p>"]
    credits = []
    for index, (_, bel, ru) in enumerate(words, 1):
        fallback.append(f"<b>{index}. {escape(bel)}</b>\n<tg-spoiler>{escape(ru)}</tg-spoiler>")
        rich.append(f"<p><b>{index}. {escape(bel)}</b><br><tg-spoiler>{escape(ru)}</tg-spoiler></p>")
        source = word_source(bel)
        if source:
            credits.append(f'<a href="{escape(source["url"], quote=True)}">{index}</a>')
    if credits:
        footer = 'Викисловарь: ' + ' · '.join(credits) + ' · <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>'
        fallback.append(f"<i>{footer}</i>")
        rich.append(f"<footer>{footer}</footer>")
    return "".join(rich), "\n\n".join(fallback)


HELP_TEXT = (
    "🌿 <b>Как устроен Зубрык</b>\n\n"
    "<b>Слова</b>\nВыбери тему, прочитай слово и открой скрытый перевод. "
    "Кнопка «Следующее слово» продолжит занятие.\n\n"
    "<b>Повторение</b>\nТест проверяет до 10 изученных слов. "
    "Напиши перевод по-белорусски — в конце увидишь результат.\n\n"
    "<b>Дуэль с другом</b>\nОтправь приглашение, отвечайте на вопросы с четырьмя вариантами. "
    "Игра идёт до первой ошибки: верный ответ даёт 1 🥔, победа — ещё 30 🥔.\n\n"
    "<b>Серия дней</b>\nНовое изученное слово поддерживает серию. "
    "Если пропустить день, серия начнётся заново.\n\n"
    "<b>Слова дня</b>\n5 слов в выбранное время. Время и отключение — в настройках.\n\n"
    "<i>В приложении — прогресс, грамматика и подготовка к ЦТ / ЦЭ.</i>"
)

HELP_RICH = (
    "<h2>🌿 Как устроен Зубрык</h2>"
    "<p>Немного беларускай каждый день.</p>"
    "<h3>Слова и повторение</h3>"
    "<p>Выбери тему, прочитай слово и открой скрытый перевод. "
    "Кнопка «Следующее слово» продолжит занятие.</p>"
    "<p>Тест проверяет до 10 изученных слов. Напиши перевод по-белорусски — "
    "в конце увидишь результат.</p>"
    "<details><summary>Дуэль и бульба</summary><p>Отправь приглашение другу. "
    "В каждом раунде — четыре варианта перевода, игра идёт до первой ошибки. "
    "Верный ответ даёт 1 🥔, победа — ещё 30 🥔.</p></details>"
    "<details><summary>Серия дней и слова дня</summary><p>Новое изученное слово "
    "поддерживает серию. Пропустишь день — серия начнётся заново.</p>"
    "<p>Слова дня — 5 слов в выбранное время. Рассылку можно отключить в настройках.</p></details>"
    "<footer>В приложении — прогресс, грамматика и подготовка к ЦТ / ЦЭ.</footer>"
)
