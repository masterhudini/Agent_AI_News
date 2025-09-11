from .rss_base import RSSFeedScraper


class EmerjScraper(RSSFeedScraper):
    """Scraper for Emerj AI Research RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="Emerj", 
            feed_url="https://emerj.com/feed/"
        )