from .pool import db_connect, db_release
from datetime import datetime, timedelta
from zubryk.config import TIMEZONE

DAILY_TIME_CHOICES = [
    ("0800", "08:00"),
    ("1000", "10:00"),
    ("1200", "12:00"),
    ("1400", "14:00"),
    ("1600", "16:00"),
    ("1800", "18:00"),
    ("2000", "20:00"),
    ("off", "❌ Не присылать"),
]
_DAILY_TIME_LABELS = dict(DAILY_TIME_CHOICES)
_USER_FIELDS = [
    "id", "name", "daily_time", "registered", "balance", "streak",
    "last_activity_date", "last_daily_sent_date", "test_queue",
]


def daily_time_label(code):
    if code is None:
        return _DAILY_TIME_LABELS["off"]
    return _DAILY_TIME_LABELS.get(code, code)


def _user_row_to_dict(row):
    if not row:
        return None
    return dict(zip(_USER_FIELDS, row))


def get_or_create_user(uid, default_name=""):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO users (id, name)
            VALUES (%s, %s)
            ON CONFLICT (id) DO NOTHING
        ''', (uid, default_name))
        conn.commit()
        cur.execute(f"SELECT {', '.join(_USER_FIELDS)} FROM users WHERE id=%s", (uid,))
        row = cur.fetchone()
        cur.close()
        return _user_row_to_dict(row)
    finally:
        db_release(conn)


def get_user(uid):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT {', '.join(_USER_FIELDS)} FROM users WHERE id=%s", (uid,))
        row = cur.fetchone()
        cur.close()
        return _user_row_to_dict(row)
    finally:
        db_release(conn)


def is_registered(uid):
    user = get_user(uid)
    return bool(user and user["registered"])


def set_name(uid, name):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET name=%s WHERE id=%s", (name, uid))
        conn.commit()
        cur.close()
    finally:
        db_release(conn)


def set_daily_time(uid, code):
    if code not in _DAILY_TIME_LABELS:
        raise ValueError("Недоступное время рассылки")
    value = None if code == "off" else code
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET daily_time=%s, registered=TRUE WHERE id=%s", (value, uid))
        conn.commit()
        cur.close()
    finally:
        db_release(conn)


def delete_user(uid):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id=%s", (uid,))
        conn.commit()
        cur.close()
    finally:
        db_release(conn)


def _touch_streak(cur, uid):
    cur.execute("SELECT last_activity_date, streak FROM users WHERE id=%s FOR UPDATE", (uid,))
    row = cur.fetchone()
    if not row:
        return
    last_date, streak = row
    today = datetime.now(TIMEZONE).date()
    if last_date == today:
        return
    if last_date == today - timedelta(days=1):
        new_streak = (streak or 0) + 1
    else:
        new_streak = 1
    cur.execute("UPDATE users SET streak=%s, last_activity_date=%s WHERE id=%s", (new_streak, today, uid))


def get_users_due_for_daily(time_code):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT id FROM users
            WHERE registered=TRUE AND daily_time=%s
              AND (last_daily_sent_date IS NULL OR last_daily_sent_date < CURRENT_DATE)
        ''', (time_code,))
        ids = [r[0] for r in cur.fetchall()]
        cur.close()
        return ids
    finally:
        db_release(conn)


def mark_daily_sent(uid):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET last_daily_sent_date=CURRENT_DATE WHERE id=%s", (uid,))
        conn.commit()
        cur.close()
    finally:
        db_release(conn)


def add_currency(uid, amount, reason):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO currency_tx (user_id, amount, reason) VALUES (%s, %s, %s)", (uid, amount, reason))
        cur.execute("UPDATE users SET balance = balance + %s WHERE id=%s RETURNING balance", (amount, uid))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        return row[0] if row else None
    finally:
        db_release(conn)


def get_balance(uid):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE id=%s", (uid,))
        row = cur.fetchone()
        cur.close()
        return row[0] if row else 0
    finally:
        db_release(conn)


def get_rating_alltime(uid, limit=10):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT id, name, balance
            FROM users
            WHERE registered=TRUE
            ORDER BY balance DESC, id
        ''')
        rows = cur.fetchall()
        cur.close()
        ranked = [(r[0], r[1], r[2], i + 1) for i, r in enumerate(rows)]
        top = ranked[:limit]
        me = next((r for r in ranked if r[0] == uid), None)
        return top, me
    finally:
        db_release(conn)


def get_rating_weekly(uid, limit=10):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT u.id, u.name, COALESCE(SUM(t.amount), 0) AS week_total
            FROM users u
            LEFT JOIN currency_tx t
                ON t.user_id = u.id
               AND t.amount > 0
               AND t.created_at >= date_trunc('week', CURRENT_TIMESTAMP)
               AND t.created_at < date_trunc('week', CURRENT_TIMESTAMP) + INTERVAL '7 days'
            WHERE u.registered = TRUE
            GROUP BY u.id, u.name
            ORDER BY week_total DESC, u.id
        ''')
        rows = cur.fetchall()
        cur.close()
        ranked = [(r[0], r[1], int(r[2]), i + 1) for i, r in enumerate(rows)]
        top = ranked[:limit]
        me = next((r for r in ranked if r[0] == uid), None)
        return top, me
    finally:
        db_release(conn)
