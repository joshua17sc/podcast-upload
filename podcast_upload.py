#!/usr/bin/python3

import os
import datetime
import re
import boto3
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Path to the WebDriver executable
driver_path = '/usr/local/bin/chromedriver'

# Ensure ChromeDriver path is correct
if not os.path.isfile(driver_path):
    raise ValueError(f"The path is not a valid file: {driver_path}")

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

# Function to extract article details from markdown
def extract_article_details(md_content):
    lines = md_content.split('\n')
    articles = []
    current_article = {}
    for line in lines:
        title_match = re.match(r'##\s*"(.*)"', line)
        url_match = re.match(r'\[Read more\]\((.*)\)', line)
        summary_match = re.match(r'^[A-Z].*', line)  # Assuming summary lines start with a capital letter
        
        if title_match:
            if current_article:
                articles.append(current_article)
                current_article = {}
            current_article['title'] = title_match.group(1)
        elif url_match:
            current_article['url'] = url_match.group(1)
        elif summary_match and line:
            if 'summary' in current_article:
                current_article['summary'] += ' ' + line
            else:
                current_article['summary'] = line
        elif not line and current_article:
            # Append the current article if there's a blank line indicating end of summary
            articles.append(current_article)
            current_article = {}
    
    if current_article:
        articles.append(current_article)
    
    return articles

# Load the markdown content
with open(post_path, 'r') as file:
    md_content = file.read()

# Extract article details
articles = extract_article_details(md_content)

# Generate podcast script
podcast_script = ""

# Introduction
podcast_script += f"Welcome to the Cybersecurity News Podcast for today. In this episode, we bring you the latest updates and insights from the cybersecurity world. For the full text, access today's post at {blog_post_url}.\n\n"

# Highlights of today's news
podcast_script += "Here's a quick look at the top headlines for today:\n"
for article in articles:
    if 'title' in article:
        podcast_script += f"- {article['title']}\n"

podcast_script += "\nLet's dive into the details of these stories.\n\n"

# Read titles and summaries
for article in articles:
    if 'title' in article and 'summary' in article:
        podcast_script += f"Title: {article['title']}\n"
        podcast_script += f"Summary: {article['summary']}\n\n"

# Farewell
podcast_script += "Thank you for listening to the Cybersecurity News Podcast. Stay safe and stay informed. Until next time, goodbye!"

# Convert script to audio using Amazon Polly
def create_audio_with_polly(script, output_path):
    polly = boto3.client('polly', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=aws_region)
    response = polly.synthesize_speech(
        Text=script,
        OutputFormat='mp3',
        VoiceId='Joanna'  # You can choose different voices available in Polly
    )
    with open(output_path, 'wb') as out:
        out.write(response['AudioStream'].read())

audio_file_path = os.path.join(output_directory, f"{episode_title}.mp3")
create_audio_with_polly(podcast_script, audio_file_path)

# Selenium part to upload the podcast episode
driver = None
try:
    # Initialize WebDriver
    options = Options()
    options.headless = True
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920x1080')
    driver = webdriver.Chrome(service=Service(driver_path), options=options)
    driver.get(login_url)

    # Log in to RSS.com
    username_input = driver.find_element(By.NAME, 'username')
    password_input = driver.find_element(By.NAME, 'password')
    username_input.send_keys(username)
    password_input.send_keys(password)
    password_input.send_keys(Keys.RETURN)

    # Wait for login to complete
    WebDriverWait(driver, 10).until(EC.url_changes(login_url))

    # Navigate to the new episode page
    driver.get(new_episode_url)

    # Upload the episode details (title, description, audio file, etc.)
    episode_title_input = driver.find_element(By.NAME, 'title')
    episode_description_input = driver.find_element(By.NAME, 'description')
    episode_audio_input = driver.find_element(By.NAME, 'audio')

    episode_title_input.send_keys(episode_title)
    episode_description_input.send_keys("Today's episode covers the latest cybersecurity news.")
    driver.execute_script("arguments[0].style.display = 'block';", episode_audio_input)  # Make the file input visible
    episode_audio_input.send_keys(audio_file_path)

    # Save the draft
    save_draft_button = driver.find_element(By.XPATH, '//button/span[contains(text(), "Save Draft")]/..')
    save_draft_button.click()

    # Wait for the draft to be saved
    WebDriverWait(driver, 10).until(EC.url_contains(drafts_url))

    # Navigate to the drafts page
    driver.get(drafts_url)

    # Locate the draft and publish it
    draft_episode = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, f'//h5[contains(text(), "{episode_title}")]/ancestor::li'))
    )
    publish_button = draft_episode.find_element(By.XPATH, './/button/span[contains(text(), "Publish")]/..')
    publish_button.click()

    # Wait for the draft to be published
    WebDriverWait(driver, 10).until(
        EC.text_to_be_present_in_element((By.XPATH, f'//h5[contains(text(), "{episode_title}")]/ancestor::li//span'), 'Published')
    )

    # Optionally, print the current URL to verify the publication
    print(driver.current_url)

finally:
    if driver:
        # Close the WebDriver session
        driver.quit()
