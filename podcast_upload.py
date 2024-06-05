#!/usr/bin/python3

import os
import datetime
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pyvirtualdisplay import Display
from selenium.common.exceptions import TimeoutException

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Path to the GeckoDriver executable
driver_path = '/usr/local/bin/geckodriver'

# Ensure GeckoDriver path is correct
if not os.path.isfile(driver_path):
    raise ValueError(f"The path is not a valid file: {driver_path}")

# Ensure the necessary environment variables are set
os.environ['webdriver.firefox.driver'] = driver_path

# Firefox options
options = Options()
options.headless = True  # Run in headless mode

# URLs
login_url = 'https://dashboard.rss.com/auth/sign-in/'
new_episode_url = 'https://dashboard.rss.com/podcasts/cybersecurity-news/new-episode/'
drafts_url = 'https://dashboard.rss.com/podcasts/cybersecurity-news/'  # URL where the drafts are listed

# User credentials from environment variables
username = os.getenv('RSS_USERNAME')
password = os.getenv('RSS_PASSWORD')

# Episode details
today = datetime.datetime.today()
episode_title = f"Cybersecurity News for {today.strftime('%d %b %Y')}"
audio_file_path = os.path.expanduser('~/cybersecurity-news/podcast_audio.mp3')

# Initialize virtual display
display = Display(visible=0, size=(1024, 768))
display.start()

try:
    logging.info('Initializing WebDriver')
    service = Service(driver_path)
    driver = webdriver.Firefox(service=service, options=options)

    logging.info('Navigating to login page')
    driver.get(login_url)

    logging.info('Entering username')
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'email'))).send_keys(username)
    logging.info('Entering password')
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'password'))).send_keys(password)
    logging.info('Submitting login form')
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'password'))).send_keys(Keys.RETURN)

    logging.info('Waiting for navigation to new episode page')
    WebDriverWait(driver, 10).until(EC.url_contains(new_episode_url))
    driver.get(new_episode_url)

    logging.info('Filling in episode details')
    episode_title_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'title')))
    episode_description_input = driver.find_element(By.NAME, 'description')
    episode_audio_input = driver.find_element(By.NAME, 'audio')

    episode_title_input.send_keys(episode_title)
    episode_description_input.send_keys("Today's episode covers the latest cybersecurity news.")
    driver.execute_script("arguments[0].style.display = 'block';", episode_audio_input)  # Make the file input visible
    episode_audio_input.send_keys(audio_file_path)

    logging.info('Saving draft')
    save_draft_button = driver.find_element(By.XPATH, '//button/span[contains(text(), "Save Draft")]/..
