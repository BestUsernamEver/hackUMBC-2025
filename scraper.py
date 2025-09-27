import os
from dotenv import load_dotenv

from google import genai

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

url = "https://web-scraping.dev/"
# later url will be searched by the ai itself or we will limit to certain sites for time reasons

# Scraps and parses HTML
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")
main_html = str(soup.select_one("main"))
# HTML -> Markdown
main_md = markdownify(main_html)

# response = client.models.generate_content(
#     model="gemini-2.5-flash",
#     contents="What is an itinerary?", 
# )

print(main_html)