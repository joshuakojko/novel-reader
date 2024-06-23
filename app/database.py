import sqlite3
import logging

DATABASE_NAME = 'library.db'
LIBRARY_TABLE = 'library'

"""
(user_id) is unique identifier for logged-in user
(base_url) is unique identifier (primary url) for novel
"""

def add_database_novel(user_id, title, current_chapter, total_chapters, status, link, base_url):
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.execute('BEGIN TRANSACTION')
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM {} WHERE user_id=? AND base_url=?'.format(LIBRARY_TABLE), (user_id, base_url))
        if c.fetchone()[0] == 0:
            c.execute('INSERT INTO library (user_id, title, current_chapter, total_chapters, status, current_url, base_url) VALUES (?, ?, ?, ?, ?, ?, ?)', (user_id, title, current_chapter, total_chapters, status, link, base_url))
            conn.commit()
        else:
            conn.rollback()
            logging.error('Attempting to add duplicate novel')

    except sqlite3.Error as error:
        if conn:
            conn.rollback()
        logging.error(f'Error in get_all_database_novels: {error}')
    finally:
        if conn:
            conn.close()

def delete_database_novels(user_id, novels_to_delete):
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.execute('BEGIN TRANSACTION')
        c = conn.cursor()
        for base_url in novels_to_delete:
            c.execute('DELETE FROM {} WHERE user_id=? AND base_url=?'.format(LIBRARY_TABLE), (user_id, base_url,))
        conn.commit()
    except sqlite3.Error as error:
        if conn:
            conn.rollback()
        logging.error(f'Error in delete_database_novels: {error}')
    finally:
        if conn:
            conn.close()

def get_all_database_novels(user_id):
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        c = conn.cursor()
        c.execute('SELECT title, current_chapter, total_chapters, status, current_url, base_url FROM {} WHERE user_id=?'.format(LIBRARY_TABLE), (user_id,))
        library = c.fetchall()
        return library
    except sqlite3.Error as error:
        logging.error(f'Error in get_all_database_novels: {error}')
    finally:
        if conn:
            conn.close()

def get_preload_urls(user_id, url):
    # Returns previous, current, and next url
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        c = conn.cursor()
        c.execute('SELECT previous_url, current_url, next_url FROM {} WHERE user_id=? AND base_url=?'.format(LIBRARY_TABLE), (user_id, url,))
        result = c.fetchone()
        if result is None:
            return (None, None, None)
        else:
            return result
    except sqlite3.Error as error:
        logging.error(f'Error in get_preload_urls: {error}')
    finally:
        if conn:
            conn.close()

def get_chapter_numbers(user_id, url):
    # Returns previous, current, and next chapter number
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        c = conn.cursor()
        c.execute('SELECT previous_chapter, current_chapter, next_chapter FROM {} WHERE user_id=? AND base_url=?'.format(LIBRARY_TABLE), (user_id, url,)) 
        result = c.fetchone()
        return (None, None, None) if result is None else result
    except sqlite3.Error as error:
        logging.error(f'Error in get_chapter_numbers: {error}')
    finally:
        if conn:
            conn.close()

def get_chapter_title_and_number(user_id, url):
    # Returns current title and chapter number 
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.execute('BEGIN TRANSACTION')
        c = conn.cursor()
        c.execute('SELECT title, current_chapter FROM {} WHERE user_id=? AND base_url=?'.format(LIBRARY_TABLE), (user_id, url,)) 
        result = c.fetchone()
        return (None, None) if result is None else result
    except sqlite3.Error as error:
        logging.error(f'Error in get_chapter_title_and_number: {error}')
    finally:
        if conn:
            conn.close()

def get_chapter_content(user_id, url, case):
    # Returns chapter content of specified case: previous, current, or next chapter 
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.execute('BEGIN TRANSACTION')
        c = conn.cursor()
        c.execute('SELECT {}_content FROM {} WHERE user_id=? AND base_url=?'.format(case, LIBRARY_TABLE), (user_id, url,)) 
        result = c.fetchone()
        return "" if result is None else result[0]
    except sqlite3.Error as error:
        logging.error(f'Error in get_chapter_content: {error}')
    finally:
        if conn:
            conn.close()

def update_chapter_content(user_id, base_url, case, chapter_number, url, content):
    # Updates chapter number, url, and content of specified case (previous, current or next chapter)
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.execute('BEGIN TRANSACTION')
        c = conn.cursor()
        c.execute('UPDATE library SET {}_chapter=?, {}_url=?, {}_content=? WHERE user_id=? AND base_url=?'.format(case, case, case), (chapter_number, url, content, user_id, base_url, ))
        conn.commit()
    except sqlite3.Error as error:
        if conn:
            conn.rollback()
        logging.error(f'Error in update_chapter_content: {error}')
    finally:
        if conn:
            conn.close()

def move_chapter(user_id, url, case1, case2):
    """
    This function updates the chapter number, url, and content of case2 > case1
    Used to move chapter data (e.g. from case2: 'previous' to case1: 'current')
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.execute('BEGIN TRANSACTION')
        c = conn.cursor()
        c.execute('UPDATE library SET {}_chapter={}_chapter, {}_url={}_url, {}_content={}_content WHERE user_id=? AND base_url=?'.format(case1, case2, case1, case2, case1, case2), (user_id, url, ))
        conn.commit()
        return
    except sqlite3.Error as error:
        if conn:
            conn.rollback()
        logging.error(f'Error in move_chapter_content: {error}')
    finally:
        if conn:
            conn.close()