import os
import datetime
import markdown2
import boto3
import requests
import logging
import json
import psutil
from pydub import AudioSegment
from bs4 import BeautifulSoup
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

def set_logging_level(level):
    logger.setLevel(level)

# Constants
MAX_TEXT_LENGTH = 3000  # AWS Polly maximum text length
PODBEAN_TOKEN_FILE = './podbean_token.json'
PODBEAN_UPLOAD_AUTHORIZE_URL = 'https://api.podbean.com/v1/files/uploadAuthorize'
PODBEAN_UPLOAD_URL = 'https://api.podbean.com/v1/files/upload'
PODBEAN_PUBLISH_URL = 'https://api.podbean.com/v1/episodes'
BITRATE = "64k"  # Bitrate for the compressed audio file

def log_resource_usage():
    process = psutil.Process(os.getpid())
    logger.info(f"Memory usage: {process.memory_info().rss / 1024 ** 2:.2f} MB")
    logger.info(f"CPU usage: {process.cpu_percent(interval=1.0)}%")

def read_file(file_path):
    logger.info(f"Reading file from {file_path}")
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise

def clean_markdown(content):
    logger.info("Cleaning markdown content")
    content = re.sub(r'^---.*?---\n', '', content, flags=re.DOTALL)
    content = re.sub(r'\[Read more\]\(.*?\)', '', content)
    return content

def parse_markdown(content):
    logger.info("Parsing markdown content")
    try:
        html_content = markdown2.markdown(content)
        articles = html_content.split('<h2>')[1:]
        article_urls = re.findall(r'\[Read more\]\((.*?)\)', content)
        return articles, article_urls
    except Exception as e:
        logger.error(f"Error parsing markdown: {e}")
        raise

def create_podcast_script(articles):
    logger.info("Creating podcast script")
    script = "<speak>This is your daily cybersecurity news for {date}.".format(date=datetime.datetime.now().strftime('%Y-%m-%d'))
    script += "<break time='2s'/>"
    
    for i, article in enumerate(articles):
        if i == 0:
            transition = "Our first article..."
        elif i == len(articles) - 1:
            transition = "Our last article..."
        else:
            transition = "Our next article..."
        
        soup = BeautifulSoup(article, 'html.parser')
        title = soup.h2.get_text(strip=True)
        content = soup.get_text(separator=" ", strip=True).replace(title, "").strip()
        
        script += "<prosody rate='medium'>{transition}</prosody><break time='1s'/>".format(transition=transition)
        script += "<prosody rate='medium'>&quot;{title}&quot; {content}</prosody><break time='2s'/>".format(title=title, content=content)
    
    script += "This has been your cybersecurity news for {date}. Tune in tomorrow and share with your friends and colleagues.</speak>".format(date=datetime.datetime.now().strftime('%Y-%m-%d'))
    logger.debug(f"Generated SSML Script: {script}")
    return script

def synthesize_speech(script, output_file):
    logger.info("Synthesizing speech using AWS Polly")
    polly = boto3.client('polly')
    try:
        response = polly.synthesize_speech(
            Text=script,
            OutputFormat='mp3',
            VoiceId='Ruth',
            Engine='neural',
            TextType='ssml'
        )
        with open(output_file, 'wb') as file:
            file.write(response['AudioStream'].read())
    except Exception as e:
        logger.error(f"Error synthesizing speech: {e}")
        raise

def compress_audio(input_file, output_file):
    logger.info("Compressing audio file")
    try:
        audio = AudioSegment.from_mp3(input_file)
        audio.export(output_file, format="mp3", bitrate=BITRATE)
        logger.info(f"Compressed audio file saved to {output_file}")
    except Exception as e:
        logger.error(f"Error compressing audio: {e}")
        raise

def read_podbean_token():
    logger.info(f"Reading Podbean token from {PODBEAN_TOKEN_FILE}")
    try:
        with open(PODBEAN_TOKEN_FILE, 'r') as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"Error reading Podbean token: {e}")
        raise

def get_podbean_upload_authorization(token):
    logger.info("Getting upload authorization from Podbean")
    try:
        response = requests.post(PODBEAN_UPLOAD_AUTHORIZE_URL, data={
            'access_token': token['access_token'],
            'filename': 'daily_cybersecurity_news.mp3',
            'filesize': os.path.getsize('episodes/daily_cybersecurity_news.mp3'),
            'content_type': 'audio/mpeg'
        })
        response.raise_for_status()
        logger.info(f"Upload authorization response status: {response.status_code}")
        return response.json()
    except Exception as e:
        logger.error(f"Error getting upload authorization: {e}")
        raise

def upload_to_podbean(upload_url, file_path):
    logger.info(f"Uploading audio file to Podbean: {file_path}")
    try:
        with open(file_path, 'rb') as file:
            response = requests.post(upload_url, files={'file': file})
            response.raise_for_status()
            logger.info(f"Podbean upload response status: {response.status_code}")
            logger.info("Upload successful")
            return response.json()
    except Exception as e:
        logger.error(f"Error uploading file to Podbean: {e}")
        raise

def publish_episode(token, file_key, description):
    logger.info("Publishing episode on Podbean")
    try:
        response = requests.post(PODBEAN_PUBLISH_URL, data={
            'access_token': token['access_token'],
            'title': f"Cybersecurity News for {datetime.datetime.now().strftime('%Y-%m-%d')}",
            'content': description,
            'media_key': file_key,
            'status': 'publish'
        })
        response.raise_for_status()
        logger.info(f"Episode publish response status: {response.status_code}")
        logger.debug(f"Episode publish response content: {response.json()}")
        return response.json()
    except Exception as e:
        logger.error(f"Error publishing episode: {e}")
        raise

def generate_html_description(articles, urls):
    logger.info("Generating HTML description")
    description = ""
    for i, article in enumerate(articles):
        soup = BeautifulSoup(article, 'html.parser')
        title = soup.h2.get_text(strip=True)
        content = soup.get_text(separator=" ", strip=True).replace(title, "").strip()
        description += f"<h2>{title}</h2><p>{content}</p>"
        if i < len(urls):
            description += f'<p><a href="{urls[i]}">Read more</a></p>'
    logger.debug(f"Generated HTML description: {description}")
    return description

def main():
    log_resource_usage()
    
    file_path = '/root/cybersecurity-news/_posts/2024-06-06-cybersecurity-news.md'
    output_file = 'episodes/daily_cybersecurity_news.mp3'
    compressed_output_file = 'episodes/daily_cybersecurity_news_compressed.mp3'
    
    content = read_file(file_path)
    cleaned_content = clean_markdown(content)
    articles, urls = parse_markdown(cleaned_content)
    
    podcast_script = create_podcast_script(articles)
    synthesize_speech(podcast_script, output_file)
    compress_audio(output_file, compressed_output_file)
    
    token = read_podbean_token()
    upload_auth = get_podbean_upload_authorization(token)
    upload_response = upload_to_podbean(upload_auth['presigned_url'], compressed_output_file)
    
    description = generate_html_description(articles, urls)
    logger.info(f"Episode content to be published: {description}")
    publish_response = publish_episode(token, upload_response['file_key'], description)
    
    logger.info(f"Episode published successfully: {publish_response}")

if __name__ == '__main__':
    main()
