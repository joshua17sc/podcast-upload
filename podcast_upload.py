#!/usr/bin/python3

import os
import datetime
import re
import boto3
import logging
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pyvirtualdisplay import Display
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Path to the GeckoDriver executable
driver_path = '/usr/local/bin/geckodriver'

# Ensure GeckoDriver path is correct
if not os.path.isfile(driver_path):
    raise ValueError(f"The path is not a valid file: {driver_path}")

# Firefox options
options = Options()
options.add_argument('--headless')  # Run in headless mode
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

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
post_path = os.path.join(post_directory, post_filename)

# Ensure the output directory exists
output_directory = '/episodes/'
if not os.path.exists(output_directory):
    os.makedirs(output_directory)

# Function to upload podcast episode to AWS S3
def upload_to_s3(file_path, bucket_name, object_name=None):
    if object_name is None:
        object_name = os.path.basename(file_path)
    s3_client = boto3.client('s3', aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key, region_name=aws_region)
    try:
        s3_client.upload_file(file_path, bucket_name, object_name)
        logging.info(f"File uploaded to S3: {object_name}")
    except Exception as e:
        logging.error(f"Failed to upload file to S3: {e}")
        raise

# Initialize virtual display
display = Display(visible=0, size=(1920, 1080))
display.start()

try:
    # Initialize WebDriver
    logging.info("Initializing WebDriver")
    driver = webdriver.Firefox(service=Service(driver_path), options=options)

    # Navigate to login page
    logging.info(f"Navigating to login page: {login_url}")
    driver.get(login_url)

    # Log in to the dashboard
    logging.info("Logging in to the dashboard")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'username')))
    username_input = driver.find_element(By.NAME, 'username')
    password_input = driver.find_element(By.NAME, 'password')
    username_input.send_keys(username)
    password_input.send_keys(password)
    password_input.send_keys(Keys.RETURN)

    # Wait for the login to complete
    WebDriverWait(driver, 10).until(EC.url_contains('dashboard.rss.com'))

    # Navigate to the new episode page
    logging.info(f"Navigating to new episode page: {new_episode_url}")
    driver.get(new_episode_url)

    # Upload episode details
    logging.info("Filling out episode details")
    audio_file_path = os.path.join(output_directory, 'episode.mp3')
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'title')))
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

finally:
    if driver:
        # Close the WebDriver session
        driver.quit()
    if display:
        # Stop the virtual display
        display.stop()
    logging.info('Closed WebDriver session and stopped virtual display')
