import os
from dotenv import load_dotenv

from google import genai

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify, MarkdownConverter
    
load_dotenv()

def md(soup, **options):
    return MarkdownConverter(**options).convert_soup(soup)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

url = "https://web-scraping.dev/"

response = requests.get(url = "https://web-scraping.dev/").content
soup = BeautifulSoup(response, "html.parser")
tutorial_HTML = soup.select_one(".tutorial")
print(md(soup=soup))