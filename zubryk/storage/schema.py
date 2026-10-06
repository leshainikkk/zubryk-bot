from .pool import db_connect, db_release
from .catalog import sync_word_catalog


def _ensure_autoincrement(cur, table, column="id"):
    seq_name = f"{table}_{column}_seq"
    cur.execute("SELECT 1 FROM pg_class WHERE relkind='S' AND relname=%s", (seq_name,))
    if cur.fetchone():
        return
    cur.execute(f"CREATE SEQUENCE {seq_name}")
    cur.execute(f"SELECT setval('{seq_name}', GREATEST(COALESCE((SELECT MAX({column}) FROM {table}), 1), 1), EXISTS(SELECT 1 FROM {table}))")
    cur.execute(f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT nextval('{seq_name}')")
    cur.execute(f"ALTER SEQUENCE {seq_name} OWNED BY {table}.{column}")


def _ensure_constraint(cur, table, constraint_name, ddl):
    cur.execute("SELECT 1 FROM pg_constraint WHERE conname=%s", (constraint_name,))
    if cur.fetchone():
        return
    cur.execute(f"ALTER TABLE {table} ADD CONSTRAINT {constraint_name} {ddl}")


def setup_database():
    conn = db_connect()
    try:
        cur = conn.cursor()

        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                name TEXT DEFAULT '',
                level TEXT DEFAULT '',
                last_word_id INTEGER DEFAULT 0,
                test_words TEXT DEFAULT '',
                daily_words TEXT DEFAULT '',
                manual_words TEXT DEFAULT ''
            )
        ''')
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS daily_time TEXT DEFAULT NULL")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS registered BOOLEAN NOT NULL DEFAULT FALSE")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS balance INTEGER NOT NULL DEFAULT 0")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS streak INTEGER NOT NULL DEFAULT 0")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_activity_date DATE")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_daily_sent_date DATE")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS test_queue TEXT NOT NULL DEFAULT ''")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT now()")
        _ensure_constraint(cur, "users", "chk_users_balance_nonneg", "CHECK (balance >= 0)")

        cur.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                key TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 0,
                active BOOLEAN NOT NULL DEFAULT TRUE
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY,
                word_bel TEXT,
                word_ru TEXT
            )
        ''')
        cur.execute("ALTER TABLE words ADD COLUMN IF NOT EXISTS group_key TEXT")
        cur.execute("ALTER TABLE words ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE")
        cur.execute("ALTER TABLE words ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT now()")
        
        
        cur.execute("UPDATE words SET active=FALSE WHERE group_key IS NULL")
        _ensure_autoincrement(cur, "words", "id")
        _ensure_constraint(
            cur, "words", "uq_words_group_bel_ru",
            "UNIQUE (group_key, word_bel, word_ru)",
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_words_group_active ON words (group_key, active)")

        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_words (
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                word_id INTEGER NOT NULL REFERENCES words(id) ON DELETE CASCADE,
                first_learned_at TIMESTAMP NOT NULL DEFAULT now(),
                last_seen_at TIMESTAMP NOT NULL DEFAULT now(),
                learned BOOLEAN NOT NULL DEFAULT TRUE,
                correct_answers INTEGER NOT NULL DEFAULT 0,
                wrong_answers INTEGER NOT NULL DEFAULT 0,
                review_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, word_id)
            )
        ''')
        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_words_user ON user_words (user_id)")

        cur.execute('''
            CREATE TABLE IF NOT EXISTS currency_tx (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                amount INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT now()
            )
        ''')
        cur.execute("CREATE INDEX IF NOT EXISTS idx_currency_tx_user_created ON currency_tx (user_id, created_at)")

        cur.execute('''
            CREATE TABLE IF NOT EXISTS games (
                id SERIAL PRIMARY KEY,
                token TEXT NOT NULL UNIQUE,
                group_key TEXT NOT NULL REFERENCES groups(key),
                creator_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                player1_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                player2_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                status TEXT NOT NULL DEFAULT 'waiting',
                round_number INTEGER NOT NULL DEFAULT 0,
                current_word_id INTEGER REFERENCES words(id),
                current_options TEXT NOT NULL DEFAULT '',
                winner_id BIGINT,
                created_at TIMESTAMP NOT NULL DEFAULT now(),
                finished_at TIMESTAMP
            )
        ''')
        cur.execute("CREATE INDEX IF NOT EXISTS idx_games_token ON games (token)")

        cur.execute('''
            CREATE TABLE IF NOT EXISTS game_answers (
                id SERIAL PRIMARY KEY,
                game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
                round_number INTEGER NOT NULL,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                word_id_chosen INTEGER,
                correct BOOLEAN NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT now(),
                UNIQUE (game_id, round_number, user_id)
            )
        ''')

        conn.commit()

        sync_word_catalog(cur)
        conn.commit()

        cur.close()
    finally:
        db_release(conn)
