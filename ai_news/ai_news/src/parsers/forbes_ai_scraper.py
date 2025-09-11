from .rss_base import RSSFeedScraper


class ForbesAIScraper(RSSFeedScraper):
    """Scraper for Forbes AI category RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="Forbes AI", 
            feed_url="https://www.forbes.com/ai/feed2/"
        )