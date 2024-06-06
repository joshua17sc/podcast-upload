import os
import datetime
import markdown2
import boto3
import requests
import logging
import json
import psutil
from pydub import AudioSegment
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
    logger.info(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
    logger.info(f"CPU usage: {psutil.cpu_percent()}%")

def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()

def clean_markdown(markdown_text):
    # Remove the date at the top
    cleaned_text = re.sub(r"^date:.*\n", "", markdown_text, flags=re.MULTILINE)
    # Remove "Read more" links
    cleaned_text = re.sub(r"\[Read more\]\(.*\)", "", cleaned_text)
    return cleaned_text

def parse_markdown(markdown_text):
    # Extract titles and content using regular expressions
    articles = re.findall(r'## (.*?)\n(.*?)(?=\n## |\Z)', markdown_text, re.DOTALL)
    return [{'title': title.strip(), 'content': content.strip()} for title, content in articles]

def create_podcast_script(articles):
    script = "<speak>"
    num_articles = len(articles)
    
    for i, article in enumerate(articles):
        if i == 0:
            script += f"Our first article, titled {article['title']}, {article['content']}<break time='2s'/>"
        elif i == num_articles - 1:
            script += f"Our last article, titled {article['title']}, {article['content']}<break time='2s'/>"
        else:
            script += f"Our next article, titled {article['title']}, {article['content']}<break time='2s'/>"
    
    script += "This has been your daily cybersecurity news. Tune in tomorrow and share with your friends and colleagues.</speak>"
    return script

def synthesize_speech(script, voice_id='Joanna'):
    polly = boto3.client('polly')
    response = polly.synthesize_speech(
        Text=script,
        OutputFormat='mp3',
        VoiceId=voice_id,
        TextType='ssml'
    )
    return response['AudioStream'].read()

def save_audio(audio_stream, file_path):
    with open(file_path, 'wb') as file:
        file.write(audio_stream)

def compress_audio(input_file, output_file):
    audio = AudioSegment.from_mp3(input_file)
    audio.export(output_file, format='mp3', bitrate=BITRATE)

def get_podbean_token():
    with open(PODBEAN_TOKEN_FILE, 'r') as file:
        return json.load(file)

def get_upload_authorization(token, file_path):
    headers = {'Authorization': f"Bearer {token['access_token']}"}
    response = requests.post(PODBEAN_UPLOAD_AUTHORIZE_URL, headers=headers, data={'file_name': os.path.basename(file_path)})
    response.raise_for_status()
    return response.json()

def upload_file_to_podbean(upload_url, file_path):
    files = {'file': open(file_path, 'rb')}
    response = requests.post(upload_url, files=files)
    response.raise_for_status()
    return response.json()

def publish_episode(token, upload_info, title, description):
    headers = {'Authorization': f"Bearer {token['access_token']}"}
    data = {
        'title': title,
        'content': description,
        'media_key': upload_info['file_key'],
        'status': 'publish'
    }
    response = requests.post(PODBEAN_PUBLISH_URL, headers=headers, data=data)
    response.raise_for_status()
    return response.json()

def main():
    markdown_file_path = '/root/cybersecurity-news/_posts/2024-06-06-cybersecurity-news.md'
    audio_file_path = '/episodes/daily_cybersecurity_news_2024-06-06.mp3'
    compressed_audio_file_path = '/episodes/daily_cybersecurity_news_2024-06-06_compressed.mp3'
    
    log_resource_usage()
    
    logger.info("Reading file from %s", markdown_file_path)
    markdown_content = read_file(markdown_file_path)
    
    logger.info("Cleaning markdown content")
    cleaned_markdown = clean_markdown(markdown_content)
    
    logger.info("Parsing markdown content")
    articles = parse_markdown(cleaned_markdown)
    
    logger.info("Creating podcast script")
    podcast_script = create_podcast_script(articles)
    logger.debug("Generated SSML Script: %s", podcast_script)
    
    logger.info("Synthesizing speech using AWS Polly")
    audio_stream = synthesize_speech(podcast_script)
    save_audio(audio_stream, audio_file_path)
    
    logger.info("Compressing audio file")
    compress_audio(audio_file_path, compressed_audio_file_path)
    
    logger.info("Reading Podbean token from %s", PODBEAN_TOKEN_FILE)
    token = get_podbean_token()
    
    logger.info("Getting upload authorization from Podbean")
    upload_auth = get_upload_authorization(token, compressed_audio_file_path)
    logger.info("Upload authorization response status: %s", upload_auth['status'])
    
    logger.info("Uploading audio file to Podbean: %s", compressed_audio_file_path)
    upload_response = upload_file_to_podbean(upload_auth['presigned_url'], compressed_audio_file_path)
    logger.info("Podbean upload response status: %s", upload_response['status'])
    
    logger.info("Upload successful")
    
    episode_title = f"Cybersecurity News for {datetime.date.today()}"
    episode_description = ''.join([f"<h2>{article['title']}</h2><p>{article['content']}</p>" for article in articles])
    
    logger.info("Episode content to be published: %s", episode_description)
    
    logger.info("Publishing episode on Podbean")
    publish_response = publish_episode(token, upload_auth, episode_title, episode_description)
    logger.info("Episode publish response status: %s", publish_response['status'])
    logger.info("Episode published successfully: %s", publish_response)

if __name__ == "__main__":
    main()
