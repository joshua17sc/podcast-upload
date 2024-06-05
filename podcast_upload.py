#!/usr/bin/python3

import os
import datetime
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pyvirtualdisplay import Display
import boto3
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
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_region = os.getenv('AWS_REGION', 'us-east-1')

# Episode details
today = datetime.datetime.today()
episode_title = f"Cybersecurity News for {today.strftime('%d %b %Y')}"
blog_post_url = f"https://joshua17sc.github.io/cybersecurity-news/{today.strftime('%Y-%m-%d')}-cybersecurity-news.html"

# Path to the blog post file
post_directory = os.path.expanduser('~/cybersecurity-news/_posts/')
post_filename = f"{today.strftime('%Y-%m-%d')}-cybersecurity-news.md"
post_filepath = os.path.join(post_directory, post_filename)

# Path to the audio file to be uploaded
audio_file_path = os.path.expanduser('~/cybersecurity-news/podcast_audio.mp3')

# Initialize virtual display
display = Display(visible=0, size=(1024, 768))
display.start()

# Initialize WebDriver without the Service class
try:
    logging.info('Initializing WebDriver')
    driver = webdriver.Firefox(executable_path=driver_path, options=options)

    # Login to the website
    logging.info('Navigating to login page')
    driver.get(login_url)

    logging.info('Entering username and password')
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'email'))).send_keys(username)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'password'))).send_keys(password)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'password'))).send_keys(Keys.RETURN)

    # Navigate to the new episode page
    logging.info('Navigating to new episode page')
    WebDriverWait(driver, 10).until(EC.url_to_be(new_episode_url))
    driver.get(new_episode_url)

    # Fill in the episode details
    logging.info('Filling in episode details')
    episode_title_input = driver.find_element(By.NAME, 'title')
    episode_description_input = driver.find_element(By.NAME, 'description')
    episode_audio_input = driver.find_element(By.NAME, 'audio')

    episode_title_input.send_keys(episode_title)
    episode_description_input.send_keys("Today's episode covers the latest cybersecurity news.")
    driver.execute_script("arguments[0].style.display = 'block';", episode_audio_input)  # Make the file input visible
    episode_audio_input.send_keys(audio_file_path)

    # Save the draft
    logging.info('Saving draft')
    save_draft_button = driver.find_element(By.XPATH, '//button/span[contains(text(), "Save Draft")]/..')
    save_draft_button.click()

    # Wait for the draft to be saved
    WebDriverWait(driver, 10).until(EC.url_contains(drafts_url))
    logging.info('Draft saved')

    # Navigate to the drafts page
    driver.get(drafts_url)

    # Locate the draft and publish it
    logging.info('Locating draft')
    draft_episode = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, f'//h5[contains(text(), "{episode_title}")]/ancestor::li'))
    )
    publish_button = draft_episode.find_element(By.XPATH, './/button/span[contains(text(), "Publish")]/..')
    logging.info('Publishing draft')
    publish_button.click()

    # Wait for the draft to be published
    WebDriverWait(driver, 10).until(
        EC.text_to_be_present_in_element((By.XPATH, f'//h5[contains(text(), "{episode_title}")]/ancestor::li//span'), 'Published')
    )
    logging.info('Draft published successfully')

    # Optionally, print the current URL to verify the publication
    logging.info(f'Published draft URL: {driver.current_url}')

except TimeoutException as e:
    logging.error(f"TimeoutException: {e}")
except Exception as e:
    logging.error(f"Exception: {e}")
finally:
    if driver:
        driver.quit()
    if display:
        display.stop()
    logging.info('Closed WebDriver session and stopped virtual display')
