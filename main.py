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
            current_article['summary'] = summary_match.group(1)
    if current_article:
        articles.append(current_article)
    return articles

# Read and parse the content of the blog post file
with open(post_path, 'r') as file:
    md_content = file.read()
articles = extract_article_details(md_content)

# Generate summary sentences for the most important articles using OpenAI
def generate_summary(article):
    if 'summary' not in article:
        return f"No summary available for the article titled '{article['title']}'."
    
    prompt = f"Write a concise summary for the following article:\n\nTitle: {article['title']}\nSummary: {article['summary']}\n\nSummary:"
    response = openai.Completion.create(
        engine="davinci",
        prompt=prompt,
        max_tokens=50
    )
    return response.choices[0].text.strip()

summaries = [generate_summary(article) for article in articles[:2]]  # Let's assume the first two articles are the most important

# Create the podcast script
script_intro = f"This is your cybersecurity news for {today.strftime('%d %b %Y')}."
script_farewell = f"This has been the cybersecurity news for {today.strftime('%d %b %Y')}. We hope to have you tune in tomorrow. Tell your friends if you got value from this podcast or leave us a comment on YouTube if there is anything you would like us to improve."

script = [script_intro]
for i, article in enumerate(articles):
    if i < 2:  # For the most important articles
        script.append(summaries[i])
    summary_text = article.get('summary', 'No summary available.')
    script.append(f"Up next, we have an article titled '{article['title']}'. You can read more at {article['url']}. Here is a brief summary: {summary_text}")

script.append(script_farewell)
podcast_script = "\n\n".join(script)

# Convert podcast script to audio using Google Text-to-Speech
def text_to_speech(text, output_file):
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    with open(output_file, "wb") as out:
        out.write(response.audio_content)
        print(f'Audio content written to file {output_file}')

audio_file_path = 'podcast_episode.mp3'
text_to_speech(podcast_script, audio_file_path)

# File paths for upload
episode_art_path = '/path/to/your/episode_art.jpg'  # Path to the episode art file
keywords = ["Keyword1", "Keyword2"]  # List of keywords to select

# Set up Chrome options for headless mode
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

# Initialize WebDriver
service = Service(driver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    # Step 1: Log in to the website
    driver.get(login_url)
    
    # Find the username and password input elements and enter credentials
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, 'username'))
    )
    username_input = driver.find_element(By.NAME, 'username')
    password_input = driver.find_element(By.NAME, 'password')
    
    username_input.send_keys(username)
    password_input.send_keys(password)
    
    # Submit the login form
    password_input.send_keys(Keys.RETURN)
    
    # Wait for login to complete
    WebDriverWait(driver, 10).until(
        EC.url_contains('dashboard')  # Adjust based on post-login URL structure
    )
    
    # Step 2: Navigate to the new episode page
    driver.get(new_episode_url)
    
    # Step 3: Fill in the episode title
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, 'title'))
    )
    title_input = driver.find_element(By.NAME, 'title')
    title_input.send_keys(episode_title)
    
    # Step 4: Fill in the episode notes
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '.tiptap.ProseMirror.HtmlEditor_editor__t7dNj'))
    )
    description_input = driver.find_element(By.CSS_SELECTOR, '.tiptap.ProseMirror.HtmlEditor_editor__t7dNj')
    description_input.send_keys(podcast_script)

    # Step 5: Select keywords
    keywords_dropdown = driver.find_element(By.CSS_SELECTOR, '.EpisodeKeywordSelect_container__GRp_2')
    keywords_dropdown.click()
    
    for keyword in keywords:
        keyword_option = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f'//div[contains(text(), "{keyword}")]'))
        )
        keyword_option.click()

    # Step 6: Upload the episode art
    episode_art_input = driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')[0]
    driver.execute_script("arguments[0].style.display = 'block';", episode_art_input)  # Make the file input visible
    episode_art_input.send_keys(episode_art_path)
    
    # Step 7: Upload the audio file
    audio_file_input = driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')[1]
    driver.execute_script("arguments[0].style.display = 'block';", audio_file_input)  # Make the file input visible
    audio_file_input.send_keys(audio_file_path)
    
    # Step 8: Save the draft
    save_draft_button = driver.find_element(By.XPATH, '//button/span[contains(text(), "Save Draft")]/..')
    save_draft_button.click()
    
    # Wait for the draft to be saved
    WebDriverWait(driver, 10).until(
        EC.url_contains(drafts_url)  # Adjust based on the URL structure after saving draft
    )
    
    # Step 9: Navigate to the drafts page
    driver.get(drafts_url)

    # Step 10: Locate the draft and publish it
    draft_episode = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, f'//h5[contains(text(), "{episode_title}")]/ancestor::li'))
    )
    publish_button = draft_episode.find_element(By.XPATH, './/button/span[contains(text(), "Publish")]/..')
    publish_button.click()

    # Wait for the draft to be published
    WebDriverWait(driver, 10).until(
        EC.text_to_be_present_in_element((By.XPATH, f'//h5[contains(text(), "{episode
