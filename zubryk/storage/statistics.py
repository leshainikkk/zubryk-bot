from datetime import datetime, timedelta

from zubryk.config import TIMEZONE
from .pool import db_connect, db_release
from .users import get_user, DAILY_TIME_CHOICES

DAY_LABELS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


def dashboard(uid, telegram_user):
    user = get_user(uid)
    if not user:
        return None
    today = datetime.now(TIMEZONE).date()
    start = today - timedelta(days=6)
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT first_learned_at::date, COUNT(*) FROM user_words
                WHERE user_id=%s AND learned=TRUE
                  AND first_learned_at >= %s AND first_learned_at < %s
                GROUP BY first_learned_at::date
            """, (uid, start, today + timedelta(days=1)))
            counts = dict(cur.fetchall())
            cur.execute("""
                SELECT g.key, g.name, COUNT(w.id),
                    COUNT(uw.word_id) FILTER (WHERE uw.learned=TRUE),
                    MAX(uw.last_seen_at), g.sort_order
                FROM groups g JOIN words w ON w.group_key=g.key AND w.active=TRUE
                LEFT JOIN user_words uw ON uw.word_id=w.id AND uw.user_id=%s
                WHERE g.active=TRUE
                GROUP BY g.key, g.name, g.sort_order
                ORDER BY (COUNT(uw.word_id) FILTER (WHERE uw.learned=TRUE) > 0) DESC,
                    MAX(uw.last_seen_at) DESC NULLS LAST, g.sort_order
                LIMIT 3
            """, (uid,))
            topics = [{"key": r[0], "name": r[1], "total": r[2], "learned": r[3]} for r in cur.fetchall()]
            cur.execute("SELECT COUNT(*) FROM user_words WHERE user_id=%s AND learned=TRUE", (uid,))
            learned_total = cur.fetchone()[0]
            cur.execute("""
                WITH ranked AS (
                    SELECT id, name, balance, DENSE_RANK() OVER (ORDER BY balance DESC) AS rank
                    FROM users WHERE registered=TRUE
                ) SELECT name, balance, rank, id=%s FROM ranked ORDER BY balance DESC, id LIMIT 5
            """, (uid,))
            leaders = [{"name": r[0] or "Без имени", "balance": r[1], "rank": r[2], "isMe": r[3]} for r in cur.fetchall()]
        days = [{"date": (start+timedelta(days=i)).isoformat(), "label": DAY_LABELS[(start+timedelta(days=i)).weekday()],
                 "count": counts.get(start+timedelta(days=i), 0), "isToday": i == 6} for i in range(7)]
        last_activity = user["last_activity_date"]
        streak = user["streak"] if last_activity and last_activity >= today-timedelta(days=1) else 0
        photo = telegram_user.get("photo_url")
        if not isinstance(photo, str) or not photo.startswith("https://"):
            photo = None
        return {"profile": {"id": uid, "name": user["name"] or "Друг", "balance": user["balance"],
                    "streak": streak, "photoUrl": photo, "dailyTime": user["daily_time"] or "off",
                    "registered": user["registered"], "learnedTotal": learned_total},
                "week": {"total": sum(d["count"] for d in days), "days": days}, "topics": topics,
                "leaders": leaders, "timezone": str(TIMEZONE),
                "topicSelection": "Недавно изученные темы, затем первые по порядку словаря",
                "dailyTimeChoices": [{"value": c, "label": l.replace("❌ ", "")} for c,l in DAILY_TIME_CHOICES]}
    finally:
        db_release(conn)
