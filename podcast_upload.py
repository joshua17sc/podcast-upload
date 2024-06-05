#!/usr/bin/python3

import os
import datetime
import logging
import mechanize
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# URLs
login_url = 'https://dashboard.rss.com/auth/sign-in/'
new_episode_url = 'https://dashboard.rss.com/podcasts/cybersecurity-news/new-episode/'
drafts_url = 'https://dashboard.rss.com/podcasts/cybersecurity-news/'

# User credentials from environment variables
username = os.getenv('RSS_USERNAME')
password = os.getenv('RSS_PASSWORD')

# Episode details
today = datetime.datetime.today()
episode_title = f"Cybersecurity News for {today.strftime('%d %b %Y')}"
audio_file_path = os.path.expanduser('~/cybersecurity-news/podcast_audio.mp3')

# Initialize mechanize browser
br = mechanize.Browser()
br.set_handle_robots(False)

# Login
logging.info('Navigating to login page')
br.open(login_url)

# Inspect the login form to find the correct field names
soup = BeautifulSoup(br.response().read(), 'html.parser')
login_form = soup.find('form')
if login_form:
    logging.info('Login form found')
    logging.info(login_form.prettify())
    email_field = login_form.find('input', {'type': 'email'})
    password_field = login_form.find('input', {'type': 'password'})
    if email_field and password_field:
        email_field_name = email_field['name']
        password_field_name = password_field['name']
        logging.info(f'Email field name: {email_field_name}')
        logging.info(f'Password field name: {password_field_name}')
    else:
        raise ValueError('Email or password field not found in the login form')
else:
    raise ValueError('Login form not found')

br.select_form(nr=0)
br.form[email_field_name] = username
br.form[password_field_name] = password
br.submit()

# Navigate to new episode page
logging.info('Navigating to new episode page')
br.open(new_episode_url)

# Fill in episode details
logging.info('Filling in episode details')
br.select_form(nr=0)
br.form['title'] = episode_title
br.form['description'] = "Today's episode covers the latest cybersecurity news."

# Since mechanize does not support file upload, we need to use requests for this part
session_cookies = br._ua_handlers['_cookies'].cookiejar
session = requests.Session()
session.cookies.update(session_cookies)

# Fetch the form page to get form data
response = session.get(new_episode_url)
soup = BeautifulSoup(response.content, 'html.parser')
form = soup.find('form')
action = form['action']

# Prepare form data for the file upload
files = {'audio': open(audio_file_path, 'rb')}
data = {input_tag['name']: input_tag.get('value', '') for input_tag in form.find_all('input')}
data.update({textarea['name']: textarea.text for textarea in form.find_all('textarea')})
data.update({select['name']: select.find('option', selected=True)['value'] for select in form.find_all('select')})

# Upload file and save draft
logging.info('Uploading audio file and saving draft')
response = session.post(action, files=files, data=data)
if response.status_code == 200:
    logging.info('Draft saved')

# Publish the draft
logging.info('Navigating to drafts page')
response = session.get(drafts_url)
soup = BeautifulSoup(response.content, 'html.parser')

logging.info('Locating draft')
draft_episode = soup.find('h5', text=episode_title)
if draft_episode:
    publish_button = draft_episode.find_next('button', text='Publish')
    if publish_button:
        publish_url = publish_button['formaction']
        response = session.post(publish_url)
        if response.status_code == 200:
            logging.info('Draft published successfully')
else:
    logging.error('Draft not found')

logging.info('Finished')
