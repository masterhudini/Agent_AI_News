from .rss_base import RSSFeedScraper


class LastWeekInAIScraper(RSSFeedScraper):
    """Scraper for Last Week in AI RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="Last Week in AI", 
            feed_url="https://lastweekin.ai/feed"
        )