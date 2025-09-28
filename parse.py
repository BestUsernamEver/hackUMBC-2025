from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, UndetectedAdapter
from crawl4ai import LLMConfig, LLMExtractionStrategy, CacheMode
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import BM25ContentFilter
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai
import asyncio
import json
import os

# Setup browser config and adapter
UNDETECTED_ADAPTER = UndetectedAdapter()

BROWSER_CONFIG = BrowserConfig(
    enable_stealth = True,
    headless = False,
    viewport_width = 1980,
    viewport_height = 1080,
    text_mode = True
)

CRAWLER_STRATEGY = AsyncPlaywrightCrawlerStrategy(
    browser_config = BROWSER_CONFIG,
    browser_adapter = UNDETECTED_ADAPTER
)

# Use options to trim our markdown and lessen input tokens
MD_GENERATOR = DefaultMarkdownGenerator(
    options = {
        "ignore_links": True,
        "body_width": 0,
        "ignore_images": True
    }
)

# Initialize environment variables
load_dotenv()

# I'm too lazy to import dataclasses and make everything actually good. 
class ErrorInfo:
    def __init__(self, err_msg, css_selector):
        self.err_msg = err_msg 
        self.css_selector = css_selector 

class ExtractInfo:
    def __init__(self, instruction, schema, css_selector):
        self.instruction = instruction
        self.schema = schema 
        self.css_selector = css_selector

class Summary(BaseModel):
    history: str 
    transportation: str 
    things_to_do: str 
    food: str 
    hotels: str 

class Event(BaseModel):
    name: str 
    time: str 
    area: str 
    relevant: bool
    #price: str

class EventList(BaseModel):
    events: list[Event]

class TravelPath(BaseModel):
    travel_methods: str 
    time: str 
    price_range: str
    relevant: bool

class Hotel(BaseModel):
    hotel_name: str 
    review_score: int 
    total_price: str
    per_night_price: str 
    miles_from_downtown: str 
    extra_info: str
    relevant: bool

class Attraction(BaseModel):
    name: str 
    location: str 
    description: str 

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
def get_attraction_info(location, goal):
    # Surprise, we're just going to call the AI outright here because TripAdvisor and Booking and Expedia are
    # all out to try to kill me :( This is horrid btw
    response = client.models.generate_content(
        model = "gemini-2.5-flash",
        contents = f"Describe 10 (or less, depends on what is available) different attractions at {location} that align with the user's goal of visiting, which is: {goal}",
        config = {
            "response_mime_type": "application/json",
            "response_schema": list[Attraction]
        }
    )
    return response.text

async def check_existence(url, fail_msg, selector):
    run_config = CrawlerRunConfig(
        css_selector = selector,
    )

    async with AsyncWebCrawler(crawler_strategy = CRAWLER_STRATEGY, config = BROWSER_CONFIG) as crawler:
        result = await crawler.arun(
            url = url,
            config = run_config
        )
        
        if not result.success:
            return False 
        
        if fail_msg in result.cleaned_html:
            return False 
        
        return True

async def get_information(url, extract_info, err_info = None):
    if err_info:
        events_exist = await check_existence(url, err_info.err_msg, err_info.css_selector)
        if not events_exist: return None 

    extraction_strategy = LLMExtractionStrategy(
        llm_config = LLMConfig(provider = "gemini/gemini-2.0-flash", api_token = os.getenv("GEMINI_API_KEY")),
        extraction_type = "schema",
        schema = TravelPath.model_json_schema(),
        instruction = extract_info.instruction,
        overlap_rate = 0.0,
        apply_chunking = False,
        #chunk_token_threshold = 10000,
        input_format = "markdown"
    )

    run_config = CrawlerRunConfig(
        css_selector = extract_info.css_selector,
        extraction_strategy = extraction_strategy,
        cache_mode = CacheMode.BYPASS,
        markdown_generator = MD_GENERATOR,
        only_text = True,
        wait_for = extract_info.css_selector # Note: needed for getpath, make workaround if needs to be removed
    )

    async with AsyncWebCrawler(crawler_strategy = CRAWLER_STRATEGY, config = BROWSER_CONFIG) as crawler:
        result = await crawler.arun(
            url = url,
            config = run_config
        )
        
        if result.success:
            #print(result.markdown)
            return result.extracted_content
            #extraction_strategy.show_usage()    
        else:
            print("We were unable to properly result the thing or something?")

async def get_hotel_info(location, start, end, goal, person_num=1, room_num=1):
    extract_info = ExtractInfo(
        instruction = f"For each listed hotel, extract its name (\"hotel_name\"), review score (\"review_score\"), prices (\"per_night_price\" and \"total_price\"), number of miles from downtown (\"miles_from_downtown\"), and any extra info (\"extra_info\") that might be important. Mark the hotel as relevant if it especially aligns with the user's purpose of visiting, which is: {goal}",
        schema = Hotel.model_json_schema(),
        css_selector = ".cca574b93c"
    )

    # I hate children so we're going to assume they don't exist. Too bad!
    url = f"https://www.booking.com/searchresults.html?ss={location}&dest_type=city&checkin={start}&checkout={end}&group_adults={person_num}&no_rooms={room_num}&group_children=0"
    info = await get_information(url, extract_info)
    return info

async def get_path(location, origin):
    extract_info = ExtractInfo(
        instruction = "For each listed way to travel, extract the travel methods, the predicted time spent, and the cost range",
        schema = TravelPath.model_json_schema(),
        css_selector = ".rounded-tr-md"
    )

    url = f"https://www.rome2rio.com/map/{origin}/{location}"
    info = await get_information(url, extract_info)
    return info

async def get_local_events(location, goal):
    err_info = ErrorInfo( # there was a note here but i think it's irrelvant now but if it becomes weird just know 
        err_msg = "Whoops, the page or event you are looking for was not found.",
        css_selector = "h1"
    )

    extract_info = ExtractInfo(
        instruction = f"Extract the name (\"name\"), time (\"time\"), area (\"area\"), and price (\"price\") of each listed event. Mark the event as relevant if it especially aligns with the user's purpose of visiting, which is: {goal}",
        schema = EventList.model_json_schema(),
        css_selector = ".SearchResultPanelContentEventCardList-module__eventList___2wk-D"
    )

    url = f"https://www.eventbrite.com/d/{location}/all-events/"
    info = await get_information(url, extract_info, err_info)
    return info
    

async def get_general_summary(location):
    err_info = ErrorInfo(
        err_msg = "There is currently no text in this page.",
        css_selector = ".noarticletext"
    )

    extract_info = ExtractInfo(
        instruction = "Extract short summary from the article about the destination's history (\"history\"), transportation (\"transportation\"), things to do (\"things_to_do\"), food (\"food\"), and hotels (\"hotels\"). If there is no/insufficient information on a certain topic, replace the summary for that topic with 'Little information.'.",
        schema = Summary.model_json_schema(),
        css_selector = ".mw-content-ltr"
    )
    url = f"https://en.wikivoyage.org/wiki/{location}"
    info = await get_information(url, extract_info, err_info)
    return info

'''
async def main():
    #await get_general_summary("Bowie")
    #print(await get_local_events("Bowie", "to embrace the arts"))

    #await get_general_summary()

    #await get_path()
    #print(await get_hotel_info('Bowie', '2025-09-28', '2025-09-30', 1, 1) )

if __name__ == "__main__":
    asyncio.run(main())
'''

print(get_attraction_info("Carson City", "sightseeing"))