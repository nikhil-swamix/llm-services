import asyncio, os, re
from crawl4ai import AsyncWebCrawler, SeedingConfig, AsyncUrlSeeder, CrawlerRunConfig, CacheMode, BFSDeepCrawlStrategy  # type: ignore
import litellm
from litellm import acompletion  # type: ignore
import aiofiles
from urllib.parse import urlparse
from tenacity import retry, stop_after_attempt, wait_random_exponential

litellm.suppress_debug_info = True


def slug_to_filename(url):
    path = urlparse(url).path
    slug = path.replace('/docs/', '').strip('/')
    if not slug:
        slug = 'index'
    safe = re.sub(r'[^\w\-_\.]', '_', slug)
    return f"{safe}.md"


async def main():
    seeder = AsyncUrlSeeder()
    crawler = AsyncWebCrawler()
    ccfg = CrawlerRunConfig(cache_mode=CacheMode.ENABLED)
    try:
        config = SeedingConfig(source="sitemap+cc", pattern="*docs/*")
        url_dicts = await seeder.urls("bits-ui.com", config)
        urls = [d["url"] for d in url_dicts]
        results = await crawler.arun_many(urls, ccfg)
        for result in results:
            filename = slug_to_filename(result.url)
            filepath = os.path.join('docs/bits-ui', filename)
            async with aiofiles.open(filepath, 'w') as f:
                await f.write(f"# {result.url}\n\n{result.markdown}")
    finally:
        await seeder.close()
        await crawler.close()


async def main2():
    config = CrawlerRunConfig(deep_crawl_strategy=BFSDeepCrawlStrategy(max_depth=1), stream=True, cache_mode=CacheMode.ENABLED, verbose=False)
    file_lock = asyncio.Lock()
    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun("https://bits-ui.com/docs", config=config)
        async for result in results:
            print(f"Processing {result.url} | MD size: {len(result.markdown) if result.markdown else 0}")

            @retry(stop=stop_after_attempt(5), wait=wait_random_exponential(min=1, max=60))
            async def process_result(res):
                os.environ['GEMINI_API_KEY'] = get_rotated_key(base_pattern="GEMINI_API_KEY*", logger=logger)  # type: ignore

                try:
                    filepath = os.path.join('../docs/bits-ui', slug_to_filename(res.url))
                    # if filepath exists, and content > 100 chars skip
                    if os.path.exists(filepath):
                        async with aiofiles.open(filepath, 'r') as f:
                            content = await f.read()
                            if len(content) > 100:
                                print(f"Skipping {res.url} | MD size: {len(res.markdown)} | File size: {len(content)}")
                                return
                    # async with file_lock:
                    #     async with aiofiles.open(filepath, 'a'): pass
                    r = await acompletion(
                        "gemini/gemini-2.5-flash",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a documentation engine, which makes docs readily available to other LLMS, given my input your task is to condense it into a markdown file. and brevity must be maintained. Do not add any content other than the markdown file. inline any code explanations, and try omitting any very trivial items",
                            },
                            {"role": "user", "content": res.markdown},
                        ],
                    )
                    content = r.choices[0].message.content

                    async with file_lock:
                        async with aiofiles.open(filepath, 'w') as f:
                            await f.write(f"# {res.url}\n\n{content}")
                except Exception as e:
                    print(f"Error processing {res.url}: {e}")

            asyncio.create_task(process_result(result))
            await asyncio.sleep(0.2)


if __name__ == "__main__":
    import sys
    from api.utils.llm import get_rotated_key
    from loguru import logger

    logger.add(sys.stdout)
    logger.info("Starting")

    # get_rotated_key(base_pattern="GEMINI_API_KEY*", logger=logger)
    os.makedirs('docs/bits-ui', exist_ok=True)
    asyncio.run(main2())
