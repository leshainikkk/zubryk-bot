from .pool import db_connect, db_release
import random
import secrets
import psycopg2
from .learning import _fetch_distractors
from .users import add_currency

_GAME_FIELDS = [
    "id", "token", "group_key", "creator_id", "player1_id", "player2_id",
    "status", "round_number", "current_word_id", "winner_id",
]


def _game_row_to_dict(row):
    if not row:
        return None
    return dict(zip(_GAME_FIELDS, row))


def create_game(creator_id, group_key):
    token = secrets.token_urlsafe(8).replace("=", "").replace("-", "").replace("_", "")
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO games (token, group_key, creator_id, player1_id, status)
            VALUES (%s, %s, %s, %s, 'waiting')
            RETURNING id
        ''', (token, group_key, creator_id, creator_id))
        game_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return game_id, token
    finally:
        db_release(conn)


def get_game(game_id):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT {', '.join(_GAME_FIELDS)} FROM games WHERE id=%s", (game_id,))
        row = cur.fetchone()
        cur.close()
        return _game_row_to_dict(row)
    finally:
        db_release(conn)


def get_game_by_token(token):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT {', '.join(_GAME_FIELDS)} FROM games WHERE token=%s", (token,))
        row = cur.fetchone()
        cur.close()
        return _game_row_to_dict(row)
    finally:
        db_release(conn)


def try_join_game(token, uid):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT id, creator_id, player1_id, player2_id, status, group_key
            FROM games WHERE token=%s FOR UPDATE
        ''', (token,))
        row = cur.fetchone()
        if not row:
            conn.commit()
            cur.close()
            return {"result": "not_found"}

        game_id, creator_id, player1_id, player2_id, status, group_key = row

        if uid in (player1_id, player2_id):
            conn.commit()
            cur.close()
            return {"result": "already_in", "game_id": game_id, "status": status, "group_key": group_key}

        if status != "waiting":
            conn.commit()
            cur.close()
            return {"result": "not_waiting", "status": status}

        cur.execute('''
            UPDATE games SET player2_id=%s, status='active'
            WHERE id=%s AND status='waiting' AND player2_id IS NULL
            RETURNING id
        ''', (uid, game_id))
        updated = cur.fetchone()
        conn.commit()
        cur.close()
        if updated:
            return {"result": "joined", "game_id": game_id, "group_key": group_key, "player1_id": player1_id}
        return {"result": "full"}
    finally:
        db_release(conn)


def start_round(game_id):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT group_key, current_word_id, round_number FROM games WHERE id=%s FOR UPDATE", (game_id,))
        row = cur.fetchone()
        if not row:
            conn.commit()
            cur.close()
            return None
        group_key, prev_word_id, round_number = row

        exclude = [prev_word_id] if prev_word_id else []
        cur.execute('''
            SELECT id, word_bel, word_ru FROM words
            WHERE group_key=%s AND active=TRUE AND NOT (id = ANY(%s))
            ORDER BY random() LIMIT 1
        ''', (group_key, exclude))
        word = cur.fetchone()
        if not word:
            cur.execute('''
                SELECT id, word_bel, word_ru FROM words
                WHERE group_key=%s AND active=TRUE
                ORDER BY random() LIMIT 1
            ''', (group_key,))
            word = cur.fetchone()
        if not word:
            conn.commit()
            cur.close()
            return None

        word_id, bel, ru = word
        distractors = _fetch_distractors(cur, group_key, word_id, ru, 3)
        options = [(word_id, ru)] + [(w[0], w[2]) for w in distractors]
        random.shuffle(options)

        new_round = round_number + 1
        options_str = ",".join(str(o[0]) for o in options)
        cur.execute('''
            UPDATE games SET current_word_id=%s, current_options=%s, round_number=%s, status='active'
            WHERE id=%s
        ''', (word_id, options_str, new_round, game_id))
        conn.commit()
        cur.close()
        return {"round": new_round, "word_id": word_id, "word_bel": bel, "options": options}
    finally:
        db_release(conn)


def get_current_round_view(game_id):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT current_word_id, current_options, round_number FROM games WHERE id=%s", (game_id,))
        row = cur.fetchone()
        if not row or not row[0]:
            cur.close()
            return None
        word_id, options_str, round_number = row
        cur.execute("SELECT word_bel FROM words WHERE id=%s", (word_id,))
        bel_row = cur.fetchone()
        if not bel_row:
            cur.close()
            return None
        option_ids = [int(x) for x in options_str.split(",") if x]
        cur.execute("SELECT id, word_ru FROM words WHERE id = ANY(%s)", (option_ids,))
        ru_map = dict(cur.fetchall())
        options = [(oid, ru_map.get(oid, "?")) for oid in option_ids]
        cur.close()
        return {"round": round_number, "word_id": word_id, "word_bel": bel_row[0], "options": options}
    finally:
        db_release(conn)


def submit_answer(game_id, uid, round_number, chosen_word_id):
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT status, round_number, current_word_id, player1_id, player2_id
            FROM games WHERE id=%s FOR UPDATE
        ''', (game_id,))
        row = cur.fetchone()
        if not row:
            conn.commit()
            cur.close()
            return {"result": "not_found"}

        status, cur_round, current_word_id, player1_id, player2_id = row

        if uid not in (player1_id, player2_id):
            conn.commit()
            cur.close()
            return {"result": "not_player"}

        if status != "active" or cur_round != round_number:
            conn.commit()
            cur.close()
            return {"result": "stale"}

        correct = (chosen_word_id == current_word_id)

        try:
            cur.execute('''
                INSERT INTO game_answers (game_id, round_number, user_id, word_id_chosen, correct)
                VALUES (%s, %s, %s, %s, %s)
            ''', (game_id, round_number, uid, chosen_word_id, correct))
        except psycopg2.IntegrityError:
            conn.rollback()
            cur.close()
            return {"result": "duplicate"}

        if not correct:
            opponent_id = player2_id if uid == player1_id else player1_id
            cur.execute('''
                UPDATE games SET status='finished', winner_id=%s, finished_at=now() WHERE id=%s
            ''', (opponent_id, game_id))
            conn.commit()
            cur.close()
            if opponent_id:
                add_currency(opponent_id, 30, "game_win")
            return {"result": "wrong", "loser_id": uid, "winner_id": opponent_id}

        conn.commit()
        new_balance = add_currency(uid, 1, "game_correct_answer")

        cur2 = conn.cursor()
        cur2.execute(
            "SELECT COUNT(*) FROM game_answers WHERE game_id=%s AND round_number=%s AND correct=TRUE",
            (game_id, round_number),
        )
        correct_count = cur2.fetchone()[0]
        conn.commit()
        cur2.close()

        if correct_count >= 2:
            next_round = start_round(game_id)
            return {"result": "advance", "balance": new_balance, "next_round": next_round}
        return {"result": "correct_wait", "balance": new_balance}
    finally:
        db_release(conn)
