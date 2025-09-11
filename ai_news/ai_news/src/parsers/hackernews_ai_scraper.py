from .rss_base import RSSFeedScraper


class HackerNewsAIScraper(RSSFeedScraper):
    """Scraper for Hacker News AI-specific RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="Hacker News AI", 
            feed_url="https://hnrss.org/newest?points=100&topic=ai"
        )