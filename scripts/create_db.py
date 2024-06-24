import sqlite3
import logging

def create_library_table():
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
                next_content TEXT,
                time TEXT
            )''')
        conn.commit()
    except sqlite3.Error as error:
        if conn:
            conn.rollback()
        logging.error(f'Error creating library table in create_db.py: {error}')
        raise
    finally:
        if conn:
            conn.close()

def create_display_preferences_table():
    conn = None
    try:
        conn = sqlite3.connect('library.db')
        conn.execute('BEGIN TRANSACTION')
        c = conn.cursor()
        c.execute(
            '''CREATE TABLE IF NOT EXISTS display_preferences (
                user_id TEXT NOT NULL PRIMARY KEY,
                mode TEXT,
                font TEXT,
                font_size INTEGER 
            )''')
        conn.commit()
    except sqlite3.Error as error:
        if conn:
            conn.rollback()
        logging.error(f'Error creating user preferences table in create_db.py: {error}')
        raise
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    create_library_table()
    create_display_preferences_table()