import os
import datetime
import re
import openai
from google.cloud import texttospeech
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

# URLs
login_url = 'https://dashboard.rss.com/auth/sign-in/'
new_episode_url = 'https://dashboard.rss.com/podcasts/cybersecurity-news/new-episode/'
drafts_url = 'https://dashboard.rss.com/podcasts/cybersecurity-news/'  # URL where the drafts are listed

# User credentials from environment variables
username = os.getenv('RSS_USERNAME')
password = os.getenv('RSS_PASSWORD')
openai.api_key = os.getenv('OPENAI_API_KEY')

# Set up Google Cloud credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/path/to/your/service-account-file.json"

# Episode details
today = datetime.datetime.today()
episode_title = f"Cybersecurity News for {today.strftime('%d %b %Y')}"

# Path to the blog post file
post_directory = os.path.expanduser('~/cybersecurity-news/_posts/')
post_filename = f"{today.strftime('%Y-%m-%d')}-cybersecurity-news.md"
post_path = os.path.join(post_directory, post_filename)

# Function to extract article details from markdown
def extract_article_details(md_content):
    lines = md_content.split('\n')
    articles = []
    current_article = {}
    for line in lines:
        title_match = re.match(r'#\s*(.*)', line)
        url_match = re.match(r'\[(.*)\]\((.*)\)', line)
        summary_match = re.match(r'>\s*(.*)', line)
        if title_match:
            if current_article:
                articles.append(current_article)
                current_article = {}
            current_article['title'] = title_match.group(1)
        if url_match:
            current_article['url'] = url_match.group(2)
        if summary_match:
            current_article['summary'] = summary_match.group
