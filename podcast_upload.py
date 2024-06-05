#!/usr/bin/python3

import os
import datetime
import logging
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

# Start a session to persist cookies
session = requests.Session()

# Login
logging.info('Navigating to login page')
response = session.get(login_url)
soup = BeautifulSoup(response.content, 'html.parser')

# Find the login form and get its action URL
login_form = soup.find('form')
login_action = login_form.get('action', login_url)
login_data = {
    'username': username,
    'password': password
}

logging.info('Submitting login form')
response = session.post(login_action, data=login_data)

# Check if login was successful
if response.url == login_url:
    logging.error('Login failed')
    exit(1)

# Navigate to new episode page
logging.info('Navigating to new episode page')
response = session.get(new_episode_url)
soup = BeautifulSoup(response.content, 'html.parser')

# Find the form for creating a new episode
form = soup.find('form')
if not form:
    logging.error('New episode form not found')
    exit(1)

# Extract form action and other details
action = form.get('action', new_episode_url)
data = {input_tag['name']: input_tag.get('value', '') for input_tag in form.find_all('input') if input_tag.get('name')}
data.update({textarea['name']: textarea.text for textarea in form.find_all('textarea') if textarea.get('name')})
data.update({select['name']: select.find('option', selected=True)['value'] for select in form.find_all('select') if select.get('name')})

# Update form data with episode details
data['title'] = episode_title
data['description'] = "Today's episode covers the latest cybersecurity news."

# Prepare the files for upload
files = {'audio': open(audio_file_path, 'rb')}

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
