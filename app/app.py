# Standard library imports
import os
import logging
import threading

# Flask, Google Oauth, and third-party imports
from flask import Flask, session, url_for, render_template, request, redirect, jsonify, abort
from authlib.integrations.flask_client import OAuth
from authlib.common.security import generate_token
import keyring
from dotenv import load_dotenv
import validators
from datetime import datetime

# Selenium imports
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# Local imports
from database import (
    add_database_novel,
    delete_database_novels,
    get_all_database_novels,
    get_chapter_title_and_number,
    get_chapter_numbers,
    get_preload_urls,
    get_chapter_content,
    update_chapter_content,
    move_chapter,
    update_read_history,
    get_display_preferences,
    update_display_preferences
    )

# Get the absolute path of the current file (main.py)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Go up one level to the project root
project_root = os.path.dirname(current_dir)

load_dotenv()

# Initialize Flask application
app = Flask(__name__, template_folder=os.path.join(project_root, 'templates'))
app.secret_key = os.getenv('SECRET_KEY')

# Initialize OAuth 2.0 client with Flask app
oauth = OAuth(app)

# Configure Selenium options for headless execution mode
options = Options()
options.add_argument('--headless')

# Google OAuth 2.0 Credentials
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = keyring.get_password('oauth', 'google_client_id')
CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'

# Login wrapper for routes
def login_wrapper(template):
    if 'user' not in session:
        return redirect('google')
    return render_template(template)

# Login wrapper for API endpoints
def login_required(f):
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect('google')
        else:
            return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/')
def index():
    return login_wrapper('index.html')

# Initializes OAuth 2.0 authentication flow
# Registers OAuth 2.0 client and redirects to Google Servers user login & consent page
# https://developers.google.com/static/identity/protocols/oauth2/images/flows/authorization-code.png
@app.route('/google')
def google():
    oauth.register('google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url=CONF_URL,
        client_kwargs={
            'scope': 'openid'
        }
    )
    session['nonce'] = generate_token() 
    return oauth.google.authorize_redirect(redirect_uri=url_for('google_auth', _external=True), nonce=session['nonce'])

# Google OAuth 2.0 callback
# Receives token response and user id, then stores the user id in the session. 
@app.route('/google/auth')
def google_auth():
    token = oauth.google.authorize_access_token()
    user_id = oauth.google.parse_id_token(token, nonce=session['nonce'])
    session['user'] = user_id.get('sub')
    return redirect('/')

@app.route('/extract')
def extract():
    return login_wrapper('extract.html')

# API endpoint to get all novels for the logged-in user in session.
# Returns server-side rendered HTML content for the novel list. 
@app.route('/api/get_novels', methods=['GET'])
@login_required
def get_novels():
    library = get_all_database_novels(session.get('user'))
    if library is None:
        return jsonify(html_content="")
    html_content = """<div class="row">"""
    for novel in library:
        html_content += """
            <div class="col-md-4 mb-4">
                <div class="card h-100">
                    <div class="card-body">
                        <h5 class="card-title">{title}</h5>
                        <p class="card-text">Current Chapter: {current_chapter} / {total_chapters}</p>
                        <p class="card-text"><small class="text-muted">Status: {status}</small></p>
                        <a href="/extract?url={current_url}" class="btn btn-primary">Read</a>
                        <div class="form-check mt-2">
                            <input type="checkbox" class="form-check-input delete-checkbox" name="delete[]" value="{base_url}" id="delete-{base_url}">
                        </div>
                    </div>
                </div>
            </div>""".format(
                current_url = novel[4],
                base_url = novel[5],
                title = novel[0],
                current_chapter = novel[1],
                total_chapters = novel[2],
                status = novel[3]
            )
    html_content += """
        </div>
        <button type="submit" class="btn btn-danger mt-3" id="delete-button">Delete Selected</button>"""
    return jsonify(html_content=html_content)

# API endpoint to add novel to session user's library. 
# Receives form data and updates library database. 
@app.route('/api/add_novel', methods=['POST'])
@login_required
def add_novel():
    user_id = session.get('user')
    title = request.form['title']
    current_chapter = request.form['current_chapter']
    total_chapters = request.form['total_chapters']
    status = request.form['status']
    link = request.form['link']
    base_url = link.split('/chapter')[0]
    add_database_novel(user_id, title, current_chapter, total_chapters, status, link, base_url, datetime.now().isoformat())
    return redirect('/')

# API endpoint to delete novels from session user's library.
# Receives form data and updates library database. 
@app.route('/api/delete_novels', methods=['POST'])
@login_required
def delete_novels():
    novels_to_delete = request.form.getlist('delete[]')
    delete_database_novels(session.get('user'), novels_to_delete)
    return redirect('/')

# API endpoint to handle chapter navigation
# Determines correct URL for navigation based on current chapter and navigation specification.
# Doesn't allow navigation while preloading. 
@app.route('/api/navigate_chapters', methods=['POST'])
@login_required
def navigate_chapters():
    url = request.get_json().get('url')
    id = request.get_json().get('id')
    prev_url, cur_url, next_url = get_preload_urls(session.get('user'), url.split('/chapter')[0])
    prev_ch_num, cur_ch_num, next_ch_num = get_chapter_numbers(session.get('user'), url.split('/chapter')[0])
    navigate_url = ""
    # Determines the navigation url based on button clicked. 
    # If chapter content not updated yet, don't navigate.
    if prev_ch_num is None or cur_ch_num is None or next_ch_num is None:
        navigate_url = ""
    else:
        # If in the middle of preloading, don't navigate. 
        if prev_ch_num + 1 != cur_ch_num or cur_ch_num + 1 != next_ch_num:
            navigate_url = ""
        else:
            # If on the first chapter, don't allow previous navigation
            if id == "previousButton" and prev_url != url and cur_ch_num > 1:
                navigate_url = prev_url
            elif id == "nextButton" and next_url != url:
                navigate_url = next_url
            elif id == "homeButton" and prev_url != url and next_url != url:
                navigate_url = "/"
    return jsonify(navigate_url=navigate_url)

# API endpoint to extract and return content of specified 'url' chapter
# Handles logic for retrieving chapter content and updating preloaded previous and next chapter data. 
@app.route('/api/extract', methods=['POST'])
@login_required
def extract_chapter():
    url = request.get_json().get('url')
    if not validators.url(url):
        return abort(404)
    base_url = url.split('/chapter')[0] # novel's primary url for database query identification
    title, chapter_number = get_chapter_title_and_number(session.get('user'), base_url)
    prev_url, cur_url, next_url = get_preload_urls(session.get('user'), base_url)
    
    if url == prev_url:
        extracted_content = get_chapter_content(session.get('user'), base_url, "previous")
        preload_async(session.get('user'), "previous", base_url, chapter_number - 1)
    elif url == cur_url:
        extracted_content = get_chapter_content(session.get('user'), base_url, "current")
        if extracted_content is None:
            extracted_content = get_reader_mode_content(url)
            update_chapter_content(session.get('user'), base_url, "current", chapter_number, url, extracted_content)
        if (prev_url is None and chapter_number > 1) or next_url is None or prev_url == cur_url or cur_url == next_url:
            preload_async(session.get('user'), "current", base_url, chapter_number)
    elif url == next_url:
        extracted_content = get_chapter_content(session.get('user'), base_url, "next")
        preload_async(session.get('user'), "next", base_url, chapter_number + 1)
    else:
        return abort(404)

    update_read_history(session.get('user'), base_url, datetime.now().isoformat())
    return jsonify(title=title, extracted_content=extracted_content)

# Asynchronously preload chapter content
# Starts a new thread to run preload function in the background. 
def preload_async(user_id, case, base_url, chapter_number):
    threading.Thread(target=preload, args=(user_id, case, base_url, chapter_number), daemon=True).start()

# Preload chapter content for smooth navigation
# Handles different preloading cases to ensure that previous, current, and next chapters are always available for quick access. 
def preload(user_id, case, base_url, chapter_number):
    """
    Precondition:
        The database contains: [previous, current, next]

    Postcondition:
        Depending on the case:
        - "previous" case: [new_previous, previous, current]    >   [previous, current, next]
        - "current" case:  [new_previous, current, new_current] >   [previous, current, next]
        - "next" case:     [current, next, new_next]            >   [previous, current, next]
    """
    if case == "current":
        if chapter_number > 1:
            preload_chapter(user_id, base_url, "previous", chapter_number - 1)
        preload_chapter(user_id, base_url, "next", chapter_number + 1)
    elif case in ["previous", "next"]:
        move_chapter(user_id, base_url, "next" if case == "previous" else "previous", "current")
        move_chapter(user_id, base_url, "current", case)
        preload_chapter_number = chapter_number - 1 if case == "previous" else chapter_number + 1
        if case == "previous" and chapter_number > 1 or case == "next":
            preload_chapter(user_id, base_url, case, preload_chapter_number)

def preload_chapter(user_id, base_url, position, chapter_number):
    preload_url = get_url_redirect(f"{base_url}/chapter-{chapter_number}")
    if preload_url:
        preload_content = get_reader_mode_content(preload_url)
        update_chapter_content(user_id, base_url, position, chapter_number, preload_url, preload_content)

# Uses Selenium webdriver to return url redirect
def get_url_redirect(url):
    try:
        with webdriver.Firefox(options=options) as driver:
            driver.get(url)
            return driver.current_url
    except Exception as error:
        logging.error(f'Error in get_url_redirect: {error}')
        return None

# Extracts the reader view content of given url
# Uses Selenium webdriver to render page and extract text from reader view. 
def get_reader_mode_content(url):
    if url is None:
        return None
    try:
        with webdriver.Firefox(options=options) as driver:
            driver.get(f'about:reader?url={url}')
            reader_content = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'moz-reader-content')))
            paragraphs = WebDriverWait(reader_content, 10).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'p')))
            return "".join(f'<p>{paragraph.text}</p>' for paragraph in paragraphs)
    except Exception as error:
        logging.error(f'Error in get_reader_mode_content: {error}')
        return None

@app.route('/api/get_display_preferences', methods=['GET'])
@login_required
def api_get_display_preferences():
    user_id = session.get('user')
    mode, font, font_size = get_display_preferences(user_id)
    return jsonify({
        'mode': mode,
        'font': font,
        'font_size': font_size
    })

@app.route('/api/update_display_preferences', methods=['POST'])
@login_required
def api_update_display_preferences():
    user_id = session.get('user')
    data = request.get_json()
    mode = data.get('mode')
    font = data.get('font')
    font_size = data.get('font_size')
    try:
        update_display_preferences(user_id, mode, font, font_size)
        return jsonify({'status': 'success'})
    except Exception as error:
        logging.error(f'Error updating display preferences: {error}')
        return jsonify({'status': 'error'})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True, use_reloader=True)