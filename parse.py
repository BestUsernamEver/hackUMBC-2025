from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, UndetectedAdapter
from crawl4ai import LLMConfig, LLMExtractionStrategy, CacheMode
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import BM25ContentFilter
from pydantic import BaseModel, Field
from dotenv import load_dotenv
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

MD_GENERATOR = DefaultMarkdownGenerator(
    options = {
        "ignore_links": True,
        "body_width": 0,
        "ignore_images": True
    }
)

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
    thingsToDo: str 
    food: str 
    hotels: str 

class Event(BaseModel):
    name: str 
    time: str 
    area: str 
    #price: str

class EventList(BaseModel):
    events: list[Event]

class TravelPath(BaseModel):
    travel_methods: str 
    time: str 
    price_range: str

class Hotel(BaseModel):
    hotel_name: str 
    review_score: int 
    prices: str 
    miles_from_downtown: int 
    extra_info: str

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
        only_text = True
    )

    async with AsyncWebCrawler(crawler_strategy = CRAWLER_STRATEGY, config = BROWSER_CONFIG) as crawler:
        result = await crawler.arun(
            url = url,
            config = run_config
        )
        
        if result.success:
            #print(result.markdown)
            print(result.extracted_content)
            #extraction_strategy.show_usage()    
        else:
            print("We were unable to properly result the thing or something?")

async def get_hotel_info():
    extract_info = ExtractInfo(
        instruction = "For each listed hotel, extract its name, review score, prices (time-specific and per night), number of miles from downtown, and any extra info that might be important.",
        schema = Hotel.model_json_schema(),
        css_selector = ".cca574b93c"
    )

    url = "https://www.booking.com/searchresults.html?ss=New+York%2C+United+States&ssne=Baltimore&ssne_untouched=Baltimore&label=gen173nr-10CAQoggJCEHNlYXJjaF9iYWx0aW1vcmVIM1gEaJkCiAEBmAEzuAEXyAEM2AED6AEB-AEBiAIBqAIBuAKU9uLGBsACAdICJDEyODA3MzgzLTVjMWQtNDA2NS05ZWJkLWJiMWRiNDIwNTNiYtgCAeACAQ&aid=304142&lang=en-us&sb=1&src_elem=sb&src=searchresults&dest_id=20088325&dest_type=city&checkin=2025-10-01&checkout=2025-10-07&group_adults=3&no_rooms=1&group_children=0"
    info = await get_information(url, extract_info)

async def get_path():
    extract_info = ExtractInfo(
        instruction = "For each listed way to travel, extract the travel methods, the predicted time spent, and the cost range.",
        schema = TravelPath.model_json_schema(),
        css_selector = ".rounded-tr-md"
    )

    url = "https://www.rome2rio.com/map/Las-Vegas/Baltimore"
    info = await get_information(url, extract_info)

async def get_local_events():
    err_info = ErrorInfo( # Note: This is useless before you have to do a wait_for! Just handle it afterward cuz fu
        err_msg = "Whoops, the page or event you are looking for was not found.",
        css_selector = "h1"
    )

    extract_info = ExtractInfo(
        instruction = "Extract the name, time, area, and price of each listed event.",
        schema = EventList.model_json_schema(),
        css_selector = ".SearchResultPanelContentEventCardList-module__eventList___2wk-D"
    )

    url = "https://www.eventbrite.com/d/md--bowie/all-events/"
    info = await get_information(url, extract_info, err_info)
    

async def get_general_summary(location):
    err_info = ErrorInfo(
        err_msg = "There is currently no text in this page.",
        css_selector = ".noarticletext"
    )

    extract_info = ExtractInfo(
        instruction = "Extract short summary from the article about the destination's history, transportation, things to do (specific for someone who enjoys the arts), food, and hotels. If there is no/insufficient information on a topic, replace with 'Not specified'.",
        schema = Summary.model_json_schema(),
        css_selector = ".mw-content-ltr"
    )
    url = f"https://en.wikivoyage.org/wiki/{location}"
    info = await get_information(url, extract_info, err_info)

async def main():
    load_dotenv()

    await get_general_summary("Bowie")
    #await get_local_events()

    #await get_general_summary()

    #await get_path()
    #await get_hotel_info() 


if __name__ == "__main__":
    asyncio.run(main())