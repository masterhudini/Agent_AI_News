from .rss_base import RSSFeedScraper


class UniteAIScraper(RSSFeedScraper):
    """Scraper for Unite.AI RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="Unite.AI", 
            feed_url="https://unite.ai/feed/"
        )