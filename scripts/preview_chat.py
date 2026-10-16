"""Generate an offline preview using the bot's actual copy and keyboards.

Run: .venv/bin/python scripts/preview_chat.py [output.html]
This does not connect to Telegram or PostgreSQL.
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from zubryk.catalog import WORD_GROUPS
from zubryk.config import TIMEZONE
from zubryk.telegram import cards, keyboards


def build_preview():
    user = {"name": "Паша", "balance": 240, "streak": 7,
            "last_activity_date": datetime.now(TIMEZONE).date(), "daily_time": "1200"}
    groups = [{"key": key, "name": value["name"]} for key, value in WORD_GROUPS.items()]
    screens = {}

    def add(key, label, html, kb):
        screens[key] = {"label": label, "html": html, "rows": kb.to_dict()["inline_keyboard"]}

    with patch.object(keyboards.db, "get_groups", return_value=groups), patch.object(keyboards, "get_mini_app_url", return_value="https://example.test/app"):
        add("menu", "Главная", cards.main_menu_text(user), keyboards.main_menu_kb())
        add("study", "Темы", cards.topics_text(), keyboards.groups_kb("sg"))
        add("word", "Новое слово", cards.study_word_text("шчыры", "искренний; чистосердечный", "Чалавек"), keyboards.study_word_kb("person"))
        add("test", "Повторение", cards.test_question_text("искренний", 3, 10, cards.test_feedback_text(True, "сябар")), keyboards.home_only_kb())
        add("result", "Итог теста", cards.test_result_text(8, 10, cards.test_feedback_text(True, "шчыры")), keyboards.test_result_kb())
        add("daily", "Слова дня", cards.daily_words_card([(1, "шчыры", "искренний"), (2, "сябар", "друг"), (3, "пяшчота", "нежность"), (4, "натхненне", "вдохновение"), (5, "утульны", "уютный")])[1], keyboards.daily_words_kb())
        add("settings", "Настройки", cards.settings_text(user, "12:00"), keyboards.settings_kb())
        add("time", "Время слов", cards.time_text(), keyboards.daily_time_kb(True, selected="1200"))
        link = "https://t.me/example_bot?start=g_demo"
        add("invite", "Приглашение", cards.invitation_text("Чалавек", link), keyboards.invitation_kb(link))
        game_kb = keyboards.types.InlineKeyboardMarkup()
        for index, option in enumerate(("медленный", "искренний", "смелый", "тихий")):
            game_kb.add(keyboards.types.InlineKeyboardButton(option, callback_data=f"ga:demo:1:{index}"))
        add("game", "Дуэль", cards.game_round_text("шчыры", 1), game_kb)
        add("help", "Помощь", cards.HELP_TEXT, keyboards.home_only_kb())
    data = json.dumps(screens, ensure_ascii=False).replace("<", "\\u003c")
    return TEMPLATE.replace("__SCREENS__", data)


TEMPLATE = r'''<!doctype html>
<html lang="ru">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Зубрык · сообщения в чате</title>
<style>
:root{color-scheme:dark;--bg:#181a1d;--panel:#202226;--message:#303235;--text:#f3f4f5;--muted:#adb2b7;--button:#3a3e42;--accent:#80c777}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}main{max-width:1440px;margin:auto;padding:38px 36px 44px}header{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:26px}header h1{font-size:26px;letter-spacing:-.6px;margin:0}header p{color:var(--muted);margin:7px 0 0;font-size:13px}.tag{color:var(--accent);border:1px solid #475a46;border-radius:20px;padding:7px 13px;white-space:nowrap;font-size:12px}nav{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:24px}nav button{font:inherit;font-size:13px;color:var(--muted);background:var(--panel);border:1px solid #383c40;border-radius:8px;padding:8px 13px;cursor:pointer}nav button[aria-pressed=true]{background:#30442f;color:#cce7c8;border-color:#63875d}.gallery{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:22px}.demo h2{font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:1.1px;color:var(--muted);margin:0 0 12px}.phone{min-height:660px;display:flex;flex-direction:column;border:1px solid #373a3e;border-radius:18px;overflow:hidden;background:#1d1f21}.chat-head{display:flex;align-items:center;gap:11px;padding:15px 18px;background:#26292c;border-bottom:1px solid #34383c}.avatar{display:grid;place-items:center;width:38px;height:38px;border-radius:50%;font-size:21px;background:#354932}.chat-head b{font-size:15px}.online{font-size:12px;color:var(--muted)}.chat{flex:1;padding:20px 14px 26px}.date{text-align:center;color:#acb1b7;font-size:11px;margin:0 auto 19px;padding:3px 10px;width:max-content;background:#303337;border-radius:12px}.bubble{background:var(--message);border-radius:13px 13px 13px 5px;padding:12px 14px 9px;overflow-wrap:anywhere;line-height:1.45;font-size:15px}.author{color:var(--accent);font-size:13px;font-weight:600;margin-bottom:8px}.body{white-space:pre-wrap}.body b{font-weight:650}.body i{color:#c1c5c9;font-style:normal;font-size:13px}.body blockquote{margin:9px 0;padding:10px 12px;border-radius:5px;background:#383c3f;border-left:3px solid var(--accent);white-space:pre-wrap}.body a{color:#a3cee9}.stamp{text-align:right;color:#a9b6bf;font-size:11px;margin-top:7px}.keys{display:flex;flex-direction:column;gap:4px;margin-top:5px}.key-row{display:flex;gap:4px}.key{flex:1;min-width:0;appearance:none;background:var(--button);color:#e8edf1;font:500 13px/1.3 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;border:0;border-radius:6px;min-height:38px;padding:10px 6px;cursor:pointer}.key.primary{background:#3577a3;color:#fff}.key.success{background:#4a7748;color:#fff}.key.danger{color:#ffd1ce;background:#794542}.key:hover{filter:brightness(1.12)}.input{padding:13px 18px;color:#8c949d;border-top:1px solid #35393e;background:#25282b;font-size:13px}tg-spoiler{display:inline;background:#666b70;border-radius:4px;color:transparent;cursor:pointer;user-select:none;padding:1px 3px;box-decoration-break:clone;-webkit-box-decoration-break:clone}tg-spoiler.revealed{color:inherit;background:#474d51;user-select:text}.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#3a4346;color:white;border:1px solid #718078;border-radius:10px;padding:12px 18px;font-size:13px;display:none;z-index:20;max-width:90vw}.footnote{color:var(--muted);font-size:12px;margin:22px 0 0}.light{color-scheme:light;--bg:#f2f4f3;--panel:#fff;--text:#242a2c;--muted:#636e72;--message:#fff;--button:#e0e8e3;--accent:#467942}.light .phone{background:#e5ece6;border-color:#c5d0c6}.light .chat-head,.light .input{background:#fafcfb;border-color:#ced7d0}.light .body i{color:#697578}.light .body blockquote{background:#edf4ed}.light .key{color:#28483c}.light .date{background:#bacbbb;color:#334738}.light .key.primary,.light .key.success{color:white}.light .body a{color:#347593}.light .chat-head{color:#29332b}
@media(max-width:1050px){main{padding:28px 20px}.gallery{grid-template-columns:repeat(2,minmax(0,1fr))}.demo:last-child{display:none}}@media(max-width:640px){main{padding:22px 14px}header{align-items:flex-start;flex-direction:column}.gallery{grid-template-columns:1fr}.demo:not(:first-child){display:none}.phone{min-height:650px}header h1{font-size:23px}}
</style>
<main>
<header><div><h1>Зубрык · прямо в чате</h1><p>Примеры из новых шаблонов сообщений. Нажми на перевод и попробуй кнопки.</p></div><span class="tag">Локальный просмотр · демоданные</span></header>
<nav aria-label="Примеры сообщений" id="nav"></nav>
<div class="gallery" id="gallery"></div>
<p class="footnote">Примерное отображение. Шрифт, цвет и форма сообщений зависят от темы и версии Telegram. Здесь кнопки переключают только примеры.</p>
</main><div class="toast" id="toast" role="status"></div>
<script>
const screens = __SCREENS__;
const nav = document.querySelector('#nav');
const gallery = document.querySelector('#gallery');
let selected = 'menu';
let nextWord = false;
function toast(text){const el=document.querySelector('#toast');el.textContent=text;el.style.display='block';clearTimeout(window.toastTimer);window.toastTimer=setTimeout(()=>el.style.display='none',2300)}
function activate(button){
 const cb=button.callback_data||'';
 if(cb.startsWith('sg:')){nextWord=!nextWord;selected='word'}
 else if(cb==='play'||cb.startsWith('pg:'))selected='invite';
 else if(cb==='settings:time')selected='time';
 else if(cb.startsWith('settime:')){selected='settings';toast('В боте выбранное время сохранится в профиле')}
 else if(cb==='settings:delete')toast('В боте откроется подтверждение удаления профиля');
 else if(cb==='settings:name')toast('В боте можно написать новое имя');
 else if(cb==='settings:support')toast('В боте откроется обращение в поддержку');
 else if(cb.startsWith('ga:')){selected='result';toast('В боте ответ проверяется для текущего раунда дуэли')}
 else if(cb.startsWith('rating'))toast('В боте здесь будет актуальный рейтинг');
 else if(cb.startsWith('groups:'))toast('В боте откроется следующая страница тем');
 else if(screens[cb])selected=cb;
 else if(button.copy_text)toast('В боте ссылка скопируется в буфер обмена');
 else if(button.url)toast('В боте откроется выбор чата для отправки приглашения');
 else if(button.web_app)toast('В боте откроется приложение Зубрыка');
 render();
}
function demo(key){
 const screen=screens[key];const section=document.createElement('section');section.className='demo';
 const heading=document.createElement('h2');heading.textContent=screen.label;section.appendChild(heading);
 const phone=document.createElement('div');phone.className='phone';
 phone.innerHTML='<div class="chat-head"><div class="avatar">🌿</div><div><b>Зубрык</b><div class="online">бот</div></div></div><div class="chat"><div class="date">Сегодня</div><div class="bubble"><div class="author">Зубрык</div><div class="body"></div><div class="stamp">12:00</div></div><div class="keys"></div></div><div class="input">Сообщение…</div>';
 phone.querySelector('.body').innerHTML=screen.html;
 for(const row of screen.rows){const el=document.createElement('div');el.className='key-row';for(const item of row){const button=document.createElement('button');button.className='key '+(item.style||'');button.textContent=item.text;button.onclick=()=>activate(item);el.appendChild(button)}phone.querySelector('.keys').appendChild(el)}
 for(const spoiler of phone.querySelectorAll('tg-spoiler')){spoiler.tabIndex=0;spoiler.setAttribute('role','button');spoiler.setAttribute('aria-label','Открыть перевод');const reveal=()=>{spoiler.classList.add('revealed');spoiler.setAttribute('aria-label',spoiler.textContent)};spoiler.onclick=reveal;spoiler.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();reveal()}}}
 section.appendChild(phone);return section;
}
function render(){gallery.replaceChildren();const keys=[selected,...['word','daily','menu','test'].filter(k=>k!==selected)].slice(0,3);keys.forEach(k=>gallery.appendChild(demo(k)));for(const button of nav.querySelectorAll('[data-key]'))button.setAttribute('aria-pressed',String(button.dataset.key===selected))}
for(const [key,screen] of Object.entries(screens)){const button=document.createElement('button');button.textContent=screen.label;button.dataset.key=key;button.setAttribute('aria-pressed','false');button.onclick=()=>{selected=key;render()};nav.appendChild(button)}
const theme=document.createElement('button');theme.textContent='Светлая / тёмная';theme.onclick=()=>document.body.classList.toggle('light');nav.appendChild(theme);
render();
</script></html>'''


if __name__ == "__main__":
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".runtime/chat-preview.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_preview(), encoding="utf-8")
    print(output.resolve())
