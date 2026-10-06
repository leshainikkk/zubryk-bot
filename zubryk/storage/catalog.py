from .pool import db_connect, db_release
from zubryk.catalog import WORD_GROUPS


def sync_word_catalog(cur):
    keys = list(WORD_GROUPS.keys())

    for order, key in enumerate(keys):
        data = WORD_GROUPS[key]
        cur.execute('''
            INSERT INTO groups (key, name, description, sort_order, active)
            VALUES (%s, %s, %s, %s, TRUE)
            ON CONFLICT (key) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                sort_order = EXCLUDED.sort_order,
                active = TRUE
        ''', (key, data["name"], data.get("description", ""), order))

    if keys:
        cur.execute("UPDATE groups SET active=FALSE WHERE key <> ALL(%s)", (keys,))
    else:
        cur.execute("UPDATE groups SET active=FALSE")

    active_triplets = set()
    for key in keys:
        for bel, ru in WORD_GROUPS[key]["words"]:
            active_triplets.add((key, bel, ru))
            cur.execute('''
                INSERT INTO words (group_key, word_bel, word_ru, active)
                VALUES (%s, %s, %s, TRUE)
                ON CONFLICT (group_key, word_bel, word_ru) DO UPDATE SET active=TRUE
            ''', (key, bel, ru))

    if keys:
        cur.execute(
            "SELECT id, group_key, word_bel, word_ru FROM words WHERE group_key = ANY(%s) AND active=TRUE",
            (keys,),
        )
        stale_ids = [r[0] for r in cur.fetchall() if (r[1], r[2], r[3]) not in active_triplets]
        if stale_ids:
            cur.execute("UPDATE words SET active=FALSE WHERE id = ANY(%s)", (stale_ids,))


def get_groups():
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT key, name, description, sort_order FROM groups WHERE active=TRUE ORDER BY sort_order, name")
        rows = cur.fetchall()
        cur.close()
        return [{"key": r[0], "name": r[1], "description": r[2], "sort_order": r[3]} for r in rows]
    finally:
        db_release(conn)


def get_group(key):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT key, name, description FROM groups WHERE key=%s AND active=TRUE", (key,))
        row = cur.fetchone()
        cur.close()
        return {"key": row[0], "name": row[1], "description": row[2]} if row else None
    finally:
        db_release(conn)


def get_group_word_count(key):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM words WHERE group_key=%s AND active=TRUE", (key,))
        n = cur.fetchone()[0]
        cur.close()
        return n
    finally:
        db_release(conn)
