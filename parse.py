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

class Summary(BaseModel):
    history: str 
    transportation: str 
    thingsToDo: str 
    food: str 
    hotels: str 

async def check_summary_exists(browser_config, crawler_strategy):
    run_config = CrawlerRunConfig(
        css_selector = ".noarticletext"
    )

    async with AsyncWebCrawler(crawler_strategy = crawler_strategy, config = browser_config) as crawler:
        result = await crawler.arun(
            url = "https://en.wikivoyage.org/wiki/Paris",
            config = run_config
        )
        print(result.cleaned_html)

        if not result.success:
            return False 
        
        if not result.cleaned_html == "<html></html>":
            return False 
        
        return True

async def get_general_summary(browser_config, crawler_strategy):
    summary_exists = await check_summary_exists(browser_config, crawler_strategy)
    if not summary_exists:
        return "We couldn't find a good summary for that location. Heres our best guess bozo"
    
    extraction_strategy = LLMExtractionStrategy(
        llm_config = LLMConfig(provider = "gemini/gemini-2.0-flash", api_token = os.getenv("GEMINI_API_KEY")),
        extraction_type = "schema",
        schema = Summary.model_json_schema(),
        instruction = "Extract short summary from the article about the destination's history, transportation, things to do, food, and hotels. If there is no/insufficient information on a topic, replace with 'Not specified'.",
        overlap_rate = 0.0,
        apply_chunking = True,
        chunk_token_threshold = 10000,
        input_format = "markdown"
    )

    print(json.dumps(Summary.model_json_schema(), indent=2))

    md_generator = DefaultMarkdownGenerator(
        options = {
            "ignore_links": True,
            "body_width": 0,
            "ignore_images": True
        }
    )

    run_config = CrawlerRunConfig(
        css_selector = ".mw-content-ltr",
        extraction_strategy = extraction_strategy,
        cache_mode = CacheMode.BYPASS,
        markdown_generator = md_generator,
        only_text = True
    )

    async with AsyncWebCrawler(crawler_strategy = crawler_strategy, config = browser_config) as crawler:
        result = await crawler.arun(
            url = "https://en.wikivoyage.org/wiki/Bowie",
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

    # Setup browser config and adapter
    undetected_adapter = UndetectedAdapter()

    browser_config = BrowserConfig(
        enable_stealth = True,
        headless = False,
        viewport_width = 1980,
        viewport_height = 1080,
        text_mode = True
    )

    crawler_strategy = AsyncPlaywrightCrawlerStrategy(
        browser_config = browser_config,
        browser_adapter = undetected_adapter
    )

    await get_general_summary(browser_config, crawler_strategy)


if __name__ == "__main__":
    asyncio.run(main())