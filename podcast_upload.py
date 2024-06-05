import os
import datetime
import markdown2
import boto3
import requests
import logging
import json
from pydub import AudioSegment

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
MAX_TEXT_LENGTH = 3000  # AWS Polly maximum text length
PODBEAN_TOKEN_FILE = './podbean_token.json'
PODBEAN_UPLOAD_URL = 'https://api.podbean.com/v1/files/upload'

def read_file(file_path):
    logging.info(f"Reading file from {file_path}")
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except Exception as e:
        logging.error(f"Error reading file: {e}")
        raise

def parse_markdown(content):
    logging.info("Parsing markdown content")
    try:
        html_content = markdown2.markdown(content)
        return html_content.split('<h2>')[1:]  # Assuming each article starts with <h2> header
    except Exception as e:
        logging.error(f"Error parsing markdown content: {e}")
        raise

def create_podcast_script(articles, today_date):
    logging.info("Creating podcast script")
    intro = f"This is your daily cybersecurity news for {today_date}."
    transitions = ["Our first article for today...", "This next article...", "Our final article for today..."]
    outro = f"This has been your cybersecurity news for {today_date}. Tune in tomorrow and share with your friends and colleagues."

    script = [intro]
    for i, article in enumerate(articles):
        script.append(transitions[min(i, len(transitions)-1)])
        script.append(markdown2.markdown(article))
        script.append("<break time='2s'/>")  # Adding pause between articles
    script.append(outro)

    return "\n".join(script)

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
    logging.info("Synthesizing speech using AWS Polly")
    polly_client = boto3.client('polly')
    chunks = split_text(script_text, MAX_TEXT_LENGTH)
    audio_segments = []

    try:
        for i, chunk in enumerate(chunks):
            logging.info(f"Synthesizing chunk {i+1}/{len(chunks)}")
            response = polly_client.synthesize_speech(
                Text=chunk,
                OutputFormat='mp3',
                VoiceId='Ruth',  # Using Ruth voice for newscasting
                Engine='neural'
            )
            temp_audio_path = f'/tmp/temp_audio_{i}.mp3'
            with open(temp_audio_path, 'wb') as file:
                file.write(response['AudioStream'].read())
            audio_segments.append(AudioSegment.from_mp3(temp_audio_path))

        combined_audio = sum(audio_segments)
        combined_audio.export(output_path, format='mp3')
        logging.info(f"Audio file saved to {output_path}")
    except Exception as e:
        logging.error(f"Error synthesizing speech: {e}")
        raise

def read_podbean_token(file_path):
    logging.info(f"Reading Podbean token from {file_path}")
    try:
        with open(file_path, 'r') as file:
            return json.load(file)['access_token']
    except Exception as e:
        logging.error(f"Error reading Podbean token: {e}")
        raise

def upload_to_podbean(audio_file_path, access_token):
    logging.info(f"Uploading audio file to Podbean: {audio_file_path}")
    try:
        with open(audio_file_path, 'rb') as file:
            files = {'file': file}
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.post(PODBEAN_UPLOAD_URL, headers=headers, files=files)
            logging.info(f"Podbean response status: {response.status_code}")
            response.raise_for_status()
            logging.info("Upload successful")
            return response.json()
    except Exception as e:
        logging.error(f"Error uploading to Podbean: {e}")
        raise

def main():
    try:
        today_date = datetime.date.today().strftime('%Y-%m-%d')
        markdown_file_path = f'~/cybersecurity-news/_posts/{today_date}-cybersecurity-news.md'
        output_audio_path = f'/episodes/daily_cybersecurity_news_{today_date}.mp3'

        markdown_content = read_file(os.path.expanduser(markdown_file_path))
        articles = parse_markdown(markdown_content)
        script_text = create_podcast_script(articles, today_date)
        synthesize_speech(script_text, output_audio_path)

        access_token = read_podbean_token(PODBEAN_TOKEN_FILE)
        upload_response = upload_to_podbean(output_audio_path, access_token)

        logging.info(f"Upload response: {upload_response}")

    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
