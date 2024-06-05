import os
import datetime
import markdown2
import boto3
import requests
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def read_markdown_file(file_path):
    try:
        with open(file_path, 'r') as file:
            logging.info(f"Reading markdown file from {file_path}")
            return file.read()
    except Exception as e:
        logging.error(f"Error reading markdown file: {e}")
        raise

def parse_markdown(content):
    try:
        logging.info("Parsing markdown content")
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

def synthesize_speech(script_text, output_path):
    try:
        logging.info("Synthesizing speech using AWS Polly")
        polly_client = boto3.Session(
            aws_access_key_id='YOUR_AWS_ACCESS_KEY',
            aws_secret_access_key='YOUR_AWS_SECRET_KEY',
            region_name='YOUR_AWS_REGION'
        ).client('polly')

        response = polly_client.synthesize_speech(
            Text=script_text,
            OutputFormat='mp3',
            VoiceId='Ruth',  # Using Ruth voice for newscasting
            Engine='neural'
        )

        with open(output_path, 'wb') as file:
            file.write(response['AudioStream'].read())
        
        logging.info(f"Audio file saved to {output_path}")
    except Exception as e:
        logging.error(f"Error synthesizing speech: {e}")
        raise

def get_podbean_access_token(client_id, client_secret):
    try:
        logging.info("Getting Podbean access token")
        response = requests.post(PODBEAN_ACCESS_TOKEN_URL, data={
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        })
        response.raise_for_status()
        return response.json()['access_token']
    except Exception as e:
        logging.error(f"Error getting Podbean access token: {e}")
        raise

def upload_to_podbean(audio_file_path, access_token):
    try:
        logging.info("Uploading audio file to Podbean")
        with open(audio_file_path, 'rb') as file:
            files = {'file': file}
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            response = requests.post(PODBEAN_UPLOAD_URL, headers=headers, files=files)
            response.raise_for_status()
            logging.info("Upload successful")
            return response.json()
    except Exception as e:
        logging.error(f"Error uploading to Podbean: {e}")
        raise

if __name__ == "__main__":
    try:
        today_date = datetime.date.today().strftime('%Y-%m-%d')
        markdown_file_path = f'/mnt/data/{today_date}-cybersecurity-news.md'
        output_audio_path = f'/episodes/daily_cybersecurity_news_{today_date}.mp3'

        markdown_content = read_markdown_file(markdown_file_path)
        articles = parse_markdown(markdown_content)
        script_text = create_podcast_script(articles, today_date)
        synthesize_speech(script_text, output_audio_path)

        PODBEAN_CLIENT_ID = 'YOUR_PODBEAN_CLIENT_ID'
        PODBEAN_CLIENT_SECRET = 'YOUR_PODBEAN_CLIENT_SECRET'
        PODBEAN_ACCESS_TOKEN_URL = 'https://api.podbean.com/v1/oauth/token'
        PODBEAN_UPLOAD_URL = 'https://api.podbean.com/v1/files/upload'

        access_token = get_podbean_access_token(PODBEAN_CLIENT_ID, PODBEAN_CLIENT_SECRET)
        upload_response = upload_to_podbean(output_audio_path, access_token)

        logging.info(f"Upload response: {upload_response}")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
