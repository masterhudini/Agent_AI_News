from .rss_base import RSSFeedScraper


class MarkTechPostScraper(RSSFeedScraper):
    """Scraper for MarkTechPost RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="MarkTechPost", 
            feed_url="https://marktechpost.com/feed/"
        )