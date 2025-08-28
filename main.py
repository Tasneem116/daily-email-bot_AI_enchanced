import os
import base64
import csv
import requests
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import pickle

# Hugging Face Transformers
from transformers import pipeline

# Gmail API scope
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# --- AI Helpers (Hugging Face) ---
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
# Initialize the pipeline for English to Hindi translation
translator = pipeline("translation_en_to_hi", model="Helsinki-NLP/opus-mt-en-hi")
motivator = pipeline("text-generation", model="distilgpt2")


def summarize_quote(quote):
    try:
        result = summarizer(quote, max_length=30, min_length=5, do_sample=False)
        return result[0]['summary_text']
    except:
        return "⚠️ Could not summarize"

def translate_quote(quote):
    try:
        result = translator(quote, max_length=100)
        return result[0]['translation_text']
    except:
        return "⚠️ Could not translate"

def motivationalize(quote):
    try:
        result = motivator(f"Make this motivational: {quote}", max_length=40, num_return_sequences=1)
        return result[0]['generated_text']
    except:
        return "⚠️ Could not generate motivation"

# --- Main Automation ---
def send_email():
    # --- 1. Scrape quotes ---
    url = "https://quotes.toscrape.com/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    quotes = soup.find_all("span", class_="text")
    authors = soup.find_all("small", class_="author")

    csv_path = "quotes.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Quote", "Author", "Summary", "Translation (HI)", "Motivational"])
        for quote, author in zip(quotes, authors):
            q = quote.text
            s = summarize_quote(q)
            t = translate_quote(q)
            m = motivationalize(q)
            writer.writerow([q, author.text, s, t, m])

    # --- 2. Gmail Auth (Colab interactive flow) ---
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)

    # --- 3. Create email ---
    sender = "syedatasneem958@gmail.com"
    receiver = "syedatasneem159@gmail.com"
    subject = "Daily Quotes Report (AI Enhanced - Hugging Face)"
    body = "Here is your AI-enhanced quotes CSV file (summarized, translated, and motivationalized)."

    message = MIMEMultipart()
    message['to'] = receiver
    message['subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    # Attach file
    with open(csv_path, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename=quotes.csv')
    message.attach(part)

    # --- 4. Send email ---
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()

    print("✅ Email with Hugging Face AI-enhanced quotes sent successfully!")

if __name__ == "__main__":
    send_email()


