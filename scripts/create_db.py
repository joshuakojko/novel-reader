import sqlite3
import logging

conn = None
try:
    conn = sqlite3.connect('library.db')
    conn.execute('BEGIN TRANSACTION')
    c = conn.cursor()
    c.execute(
        '''CREATE TABLE IF NOT EXISTS library (
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            current_chapter INTEGER,
            total_chapters INTEGER,
            status TEXT,
            base_url TEXT,
            current_url TEXT,
            current_content TEXT,
            previous_chapter INTEGER DEFAULT 0,
            previous_url TEXT,
            previous_content TEXT,
            next_chapter INTEGER DEFAULT 0,
            next_url TEXT,
            next_content TEXT
        )''')
    conn.commit()
except sqlite3.Error as error:
    if conn:
        conn.rollback()
    logging.error(f'Error in create_db.py: {error}')
    raise
finally:
    if conn:
        conn.close()