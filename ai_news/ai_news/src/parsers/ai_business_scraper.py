from .rss_base import RSSFeedScraper


class AIBusinessScraper(RSSFeedScraper):
    """Scraper for AI Business RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="AI Business", 
            feed_url="https://aibusiness.com/feed/"
        )