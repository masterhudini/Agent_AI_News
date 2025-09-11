from .rss_base import RSSFeedScraper


class FastMLScraper(RSSFeedScraper):
    """Scraper for FastML RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="FastML", 
            feed_url="https://fastml.com/feed/"
        )