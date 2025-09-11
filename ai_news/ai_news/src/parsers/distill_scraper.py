from .rss_base import RSSFeedScraper


class DistillScraper(RSSFeedScraper):
    """Scraper for Distill RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="Distill", 
            feed_url="https://distill.pub/feed.xml"
        )