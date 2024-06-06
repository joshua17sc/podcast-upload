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
    # Remove the first line containing the date
    content = re.sub(r'^---.*?---\n', '', content, flags=re.DOTALL)
    # Remove "Read more" links
    content = re.sub(r'\[Read more\]\(.*?\)', '', content)
    return content

def parse_markdown(content):
    logger.info("Parsing markdown content")
    try:
        html_content = markdown2.markdown(content)
        articles = html_content.split('<h2>')[1:]  # Assuming each article starts with <h2> header
        parsed_articles = [BeautifulSoup(article, 'html.parser') for article in articles]
        return parsed_articles
    except Exception as e:
        logger.error(f"Error parsing markdown content: {e}")
        raise

def create_podcast_script(articles, today_date):
    logger.info("Creating podcast script")
    intro = f"This is your daily cybersecurity news for {today_date}."
    transitions = ["Our first article for today...", "This next article...", "Our final article for today..."]
    outro = f"This has been your cybersecurity news for {today_date}. Tune in tomorrow and share with your friends and colleagues."

    script = [intro]
    for i, article in enumerate(articles):
        script.append(transitions[min(i, len(transitions)-1)])
        script.append(article.get_text())
    script.append(outro)

    full_script = "\n".join(script)
    logger.debug(f"Generated Script: {full_script}")
    return full_script

def split_text(text, max_length):
    chunks = []
    while len(text) > max_length:
        split_index = text[:max_length].rfind('. ')
        if split_index == -1:
            split_index = max_length
        chunks.append(text[:split_index + 1])
        text = text[split_index + 1:]
    chunks.append(text)
    return chunks

def synthesize_speech(script_text, output_path):
    logger.info("Synthesizing speech using AWS Polly")
    polly_client = boto3.client('polly')
    chunks = split_text(script_text, MAX_TEXT_LENGTH)
    audio_segments = []

    try:
        for i, chunk in enumerate(chunks):
            logger.info(f"Synthesizing chunk {i+1}/{len(chunks)}")
            logger.debug(f"Text Chunk: {chunk}")
            response = polly_client.synthesize_speech(
                Text=chunk,
                OutputFormat='mp3',
                TextType='text',
                VoiceId='Ruth',  # Using Ruth voice for newscasting
                Engine='neural'
            )
            temp_audio_path = f'/tmp/temp_audio_{i}.mp3'
            with open(temp_audio_path, 'wb') as file:
                file.write(response['AudioStream'].read())
            audio_segments.append(AudioSegment.from_mp3(temp_audio_path))
            os.remove(temp_audio_path)  # Delete temporary file to free up memory

        combined_audio = sum(audio_segments)
        compressed_audio_path = output_path.replace(".mp3", "_compressed.mp3")
        combined_audio.export(compressed_audio_path, format='mp3', bitrate=BITRATE)
        logger.info(f"Compressed audio file saved to {compressed_audio_path}")
        log_resource_usage()  # Log resource usage after processing
        return compressed_audio_path
    except Exception as e:
        logger.error(f"Error synthesizing speech: {e}")
        raise

def read_podbean_token(file_path):
    logger.info(f"Reading Podbean token from {file_path}")
    try:
        with open(file_path, 'r') as file:
            return json.load(file)['access_token']
    except Exception as e:
        logger.error(f"Error reading Podbean token: {e}")
        raise

def get_upload_authorization(token, filename, filesize, content_type='audio/mpeg'):
    try:
        logger.info("Getting upload authorization from Podbean")
        params = {
            'access_token': token,
            'filename': filename,
            'filesize': filesize,
            'content_type': content_type
        }
        response = requests.get(PODBEAN_UPLOAD_AUTHORIZE_URL, params=params)
        logger.info(f"Upload authorization response status: {response.status_code}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error getting upload authorization: {e}")
        raise

def upload_to_podbean(upload_url, audio_file_path):
    logger.info(f"Uploading audio file to Podbean: {audio_file_path}")
    try:
        with open(audio_file_path, 'rb') as file:
            response = requests.put(upload_url, data=file)
            logger.info(f"Podbean upload response status: {response.status_code}")
            response.raise_for_status()
            logger.info("Upload successful")
    except Exception as e:
        logger.error(f"Error uploading to Podbean: {e}")
        raise

def publish_episode(token, title, content, media_key):
    try:
        logger.info("Publishing episode on Podbean")
        data = {
            'access_token': token,
            'title': title,
            'content': content,
            'status': 'publish',
            'type': 'public',
            'media_key': media_key
        }
        response = requests.post(PODBEAN_PUBLISH_URL, data=data)
        logger.info(f"Episode publish response status: {response.status_code}")
        response.raise_for_status()
        logger.info("Episode published successfully")
        return response.json()
    except Exception as e:
        logger.error(f"Error publishing episode: {e}")
        raise

def create_html_description(articles):
    logger.info("Creating HTML description for the podcast")
    description = ""
    for article in articles:
        header = article.find('h2')
        if header:
            description += f"<h2>{header.text}</h2>"
        links = article.find_all('a')
        for link in links:
            description += f'<p><a href="{link["href"]}">{link.text}</a></p>'
        description += f'<p>{article.get_text()}</p>'
    return description

def main():
    try:
        today_date = datetime.date.today().strftime('%Y-%m-%d')
        markdown_file_path = f'~/cybersecurity-news/_posts/{today_date}-cybersecurity-news.md'
        output_audio_path = f'/episodes/daily_cybersecurity_news_{today_date}.mp3'

        markdown_content = read_file(os.path.expanduser(markdown_file_path))
        cleaned_content = clean_markdown(markdown_content)
        parsed_articles = parse_markdown(cleaned_content)
        script_text = create_podcast_script(parsed_articles, today_date)
        compressed_audio_path = synthesize_speech(script_text, output_audio_path)

        access_token = read_podbean_token(PODBEAN_TOKEN_FILE)
        file_size = os.path.getsize(compressed_audio_path)
        filename = os.path.basename(compressed_audio_path)
        
        upload_auth_response = get_upload_authorization(access_token, filename, file_size)

        upload_to_podbean(upload_auth_response['presigned_url'], compressed_audio_path)

        episode_title = f"Cybersecurity News for {today_date}"
        episode_content = create_html_description(parsed_articles)
        publish_response = publish_episode(access_token, episode_title, episode_content, upload_auth_response['file_key'])

        logger.info(f"Publish response: {publish_response}")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
 
if __name__ == "__main__":
    # Set logging level to DEBUG for more detailed logs.
    set_logging_level(logging.DEBUG)
    main()
