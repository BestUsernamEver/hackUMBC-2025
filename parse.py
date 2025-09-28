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

async def check_existence(url, fail_msg, selector):
    run_config = CrawlerRunConfig(
        css_selector = selector
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
    
#sc-dpDFRI cEqDEX for rome2rio

async def get_path():
    events_exist = await check_existence(
        "https://www.rome2rio.com/map/Las%20Vegas/Baltimore",
        "An error occurred. Please try again shortly.",
        "sc-dpDFRI cEqDEX"
    )
    if not events_exist:
        return "I'm going to touch you okay BAKA BOY"
    
    extraction_strategy = LLMExtractionStrategy(
        llm_config = LLMConfig(provider = "gemini/gemini-2.0-flash", api_token = os.getenv("GEMINI_API_KEY")),
        extraction_type = "schema",
        schema = EventList.model_json_schema(),
        instruction = "Extract the name, time, area, and price of each listed event.",
        overlap_rate = 0.0,
        apply_chunking = False,
        #chunk_token_threshold = 10000,
        input_format = "markdown"
    )

async def get_local_events():
    events_exist = await check_existence(
        "https://www.eventbrite.com/d/md--bowie/all-events/", 
        "Whoops, the page or event you are looking for was not found.", 
        "h1"
    )
    if not events_exist:
        return "We didn't find any good ongoing/preparing local events for that location."
    
    extraction_strategy = LLMExtractionStrategy(
        llm_config = LLMConfig(provider = "gemini/gemini-2.0-flash", api_token = os.getenv("GEMINI_API_KEY")),
        extraction_type = "schema",
        schema = EventList.model_json_schema(),
        instruction = "Extract the name, time, area, and price of each listed event.",
        overlap_rate = 0.0,
        apply_chunking = False,
        #chunk_token_threshold = 10000,
        input_format = "markdown"
    )

    run_config = CrawlerRunConfig(
        css_selector = ".SearchResultPanelContentEventCardList-module__eventList___2wk-D",
        extraction_strategy = extraction_strategy,
        cache_mode = CacheMode.BYPASS,
        markdown_generator = MD_GENERATOR,
        only_text = True
    )

    async with AsyncWebCrawler(crawler_strategy = CRAWLER_STRATEGY, config = BROWSER_CONFIG) as crawler:
        result = await crawler.arun(
            url = "https://www.eventbrite.com/d/md--bowie/all-events/",
            config = run_config
        )
        
        if result.success:
            #print(result.markdown)
            print(result.extracted_content)
            #extraction_strategy.show_usage()    
        else:
            print("KYS")
    

async def get_general_summary():
    summary_exists = await check_existence(
        "https://en.wikivoyage.org/wiki/Paris", 
        "There is currently no text in this page.", 
        ".noarticletext"
    )
    if not summary_exists:
        return "We couldn't find a good summary for that location."
    
    extraction_strategy = LLMExtractionStrategy(
        llm_config = LLMConfig(provider = "gemini/gemini-2.0-flash", api_token = os.getenv("GEMINI_API_KEY")),
        extraction_type = "schema",
        schema = Summary.model_json_schema(),
        instruction = "Extract short summary from the article about the destination's history, transportation, things to do (specific for someone who enjoys the arts), food, and hotels. If there is no/insufficient information on a topic, replace with 'Not specified'.",
        overlap_rate = 0.0,
        apply_chunking = False,
        #chunk_token_threshold = 10000,
        input_format = "markdown"
    )

    #print(json.dumps(Summary.model_json_schema(), indent=2))

    run_config = CrawlerRunConfig(
        css_selector = ".mw-content-ltr",
        extraction_strategy = extraction_strategy,
        cache_mode = CacheMode.BYPASS,
        markdown_generator = MD_GENERATOR,
        only_text = True
    )

    async with AsyncWebCrawler(crawler_strategy = CRAWLER_STRATEGY, config = BROWSER_CONFIG) as crawler:
        result = await crawler.arun(
            url = "https://en.wikivoyage.org/wiki/Paris",
            config = run_config
        )
        
        if result.success:
            #print(result.markdown)
            print(result.extracted_content)
            #extraction_strategy.show_usage()    
        else:
            print("KYS")

async def main():
    load_dotenv()

    await get_general_summary()
    #await get_local_events()


if __name__ == "__main__":
    asyncio.run(main())