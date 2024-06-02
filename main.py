import os
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

# Episode details
episode_title = "New Episode Title"
episode_description = "This is a description for the new episode."
audio_file_path = '/path/to/your/audio_file'  # Path to the audio file
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
    description_input.send_keys(episode_description)

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
        EC.text_to_be_present_in_element((By.XPATH, f'//h5[contains(text(), "{episode_title}")]/ancestor::li//span'), 'Published')
    )
    
    # Optionally, print the current URL to verify the draft saving
    print(driver.current_url)

finally:
    # Close the WebDriver session
    driver.quit()
