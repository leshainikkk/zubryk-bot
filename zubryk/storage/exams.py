import json

from psycopg2.extras import Json

from .pool import db_connect, db_release


def setup_exam_storage():
    conn=db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS exam_attempts (
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    question_id TEXT NOT NULL,
                    content_version TEXT NOT NULL,
                    answers JSONB NOT NULL,
                    correct BOOLEAN NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT now(),
                    PRIMARY KEY (user_id, question_id, content_version)
                )
            """)
        conn.commit()
    finally:
        db_release(conn)


def get_attempts(uid, version):
    conn=db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT question_id, answers, correct FROM exam_attempts WHERE user_id=%s AND content_version=%s",(uid,version))
            return {r[0]: {"answers": r[1], "correct": r[2]} for r in cur.fetchall()}
    finally:
        db_release(conn)


def save_attempt(uid, question_id, version, answers, correct):
    conn=db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO exam_attempts(user_id,question_id,content_version,answers,correct)
                VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING
            """, (uid,question_id,version,Json(sorted(answers)),correct))
            cur.execute("SELECT answers,correct FROM exam_attempts WHERE user_id=%s AND question_id=%s AND content_version=%s",(uid,question_id,version))
            row=cur.fetchone()
        conn.commit()
        return {"answers": row[0], "correct": row[1]}
    finally:
        db_release(conn)
