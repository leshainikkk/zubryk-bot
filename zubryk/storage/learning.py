from .pool import db_connect, db_release
import random
from .users import _touch_streak


def get_next_new_word(uid, group_key):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT w.id, w.word_bel, w.word_ru
            FROM words w
            WHERE w.group_key=%s AND w.active=TRUE
              AND NOT EXISTS (SELECT 1 FROM user_words uw WHERE uw.user_id=%s AND uw.word_id=w.id)
            ORDER BY w.id
            LIMIT 1
        ''', (group_key, uid))
        row = cur.fetchone()
        cur.close()
        return row
    finally:
        db_release(conn)


def get_next_new_words_multi(uid, limit=5):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT w.id, w.word_bel, w.word_ru
            FROM words w
            JOIN groups g ON g.key = w.group_key AND g.active = TRUE
            WHERE w.active = TRUE
              AND NOT EXISTS (SELECT 1 FROM user_words uw WHERE uw.user_id=%s AND uw.word_id=w.id)
            ORDER BY g.sort_order, w.id
            LIMIT %s
        ''', (uid, limit))
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        db_release(conn)


def mark_word_learned(uid, word_id):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO user_words (user_id, word_id)
            VALUES (%s, %s)
            ON CONFLICT (user_id, word_id) DO UPDATE SET last_seen_at = now()
            RETURNING (xmax = 0) AS inserted
        ''', (uid, word_id))
        inserted = bool(cur.fetchone()[0])
        if inserted:
            _touch_streak(cur, uid)
        conn.commit()
        cur.close()
        return inserted
    finally:
        db_release(conn)


def get_learned_word_ids(uid):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT word_id FROM user_words WHERE user_id=%s AND learned=TRUE", (uid,))
        ids = [r[0] for r in cur.fetchall()]
        cur.close()
        return ids
    finally:
        db_release(conn)


def _fetch_distractors(cur, group_key, correct_word_id, correct_ru, n=3):
    cur.execute('''
        SELECT id, word_bel, word_ru FROM words
        WHERE group_key=%s AND active=TRUE AND id <> %s AND word_ru <> %s
        ORDER BY random() LIMIT %s
    ''', (group_key, correct_word_id, correct_ru, max(n * 4, 12)))
    seen_ru = {correct_ru}
    result = []
    for wid, bel, ru in cur.fetchall():
        if ru in seen_ru:
            continue
        seen_ru.add(ru)
        result.append((wid, bel, ru))
        if len(result) >= n:
            return result

    if len(result) < n:
        need = n - len(result)
        exclude_ids = [correct_word_id] + [r[0] for r in result]
        cur.execute('''
            SELECT id, word_bel, word_ru FROM words
            WHERE active=TRUE AND NOT (id = ANY(%s)) AND word_ru <> %s
            ORDER BY random() LIMIT %s
        ''', (exclude_ids, correct_ru, max(need * 4, 12)))
        for wid, bel, ru in cur.fetchall():
            if ru in seen_ru:
                continue
            seen_ru.add(ru)
            result.append((wid, bel, ru))
            if len(result) >= n:
                break
    return result


def get_words_by_ids(ids):
    if not ids:
        return []
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, word_bel, word_ru, group_key FROM words WHERE id = ANY(%s)", (list(ids),))
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        db_release(conn)


def start_test(uid, max_words=10):
    learned_ids = get_learned_word_ids(uid)
    if not learned_ids:
        return 0
    random.shuffle(learned_ids)
    chosen = learned_ids[:max_words]
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET test_queue=%s WHERE id=%s", (",".join(map(str, chosen)), uid))
        conn.commit()
        cur.close()
    finally:
        db_release(conn)
    return len(chosen)


def get_next_test_word(uid):
    conn = db_connect()
    try:
        cur = conn.cursor()
        while True:
            cur.execute("SELECT test_queue FROM users WHERE id=%s", (uid,))
            row = cur.fetchone()
            if not row or not row[0]:
                cur.close()
                return None
            ids = [x for x in row[0].split(",") if x]
            if not ids:
                cur.close()
                return None
            first_id = int(ids[0])
            cur.execute("SELECT id, word_bel, word_ru FROM words WHERE id=%s AND active=TRUE", (first_id,))
            word = cur.fetchone()
            if word:
                cur.close()
                return word
            rest = ids[1:]
            cur.execute("UPDATE users SET test_queue=%s WHERE id=%s", (",".join(rest), uid))
            conn.commit()
    finally:
        db_release(conn)


def pop_test_word(uid):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT test_queue FROM users WHERE id=%s", (uid,))
        row = cur.fetchone()
        if row and row[0]:
            ids = [x for x in row[0].split(",") if x][1:]
            cur.execute("UPDATE users SET test_queue=%s WHERE id=%s", (",".join(ids), uid))
            conn.commit()
        cur.close()
    finally:
        db_release(conn)


def record_test_answer(uid, word_id, correct):
    conn = db_connect()
    try:
        cur = conn.cursor()
        column = "correct_answers" if correct else "wrong_answers"
        cur.execute(f'''
            UPDATE user_words
            SET {column} = {column} + 1, review_count = review_count + 1, last_seen_at = now()
            WHERE user_id=%s AND word_id=%s
        ''', (uid, word_id))
        conn.commit()
        cur.close()
    finally:
        db_release(conn)
