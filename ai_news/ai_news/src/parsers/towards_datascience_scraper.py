from .rss_base import RSSFeedScraper


class TowardsDataScienceScraper(RSSFeedScraper):
    """Scraper for Towards Data Science RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="Towards Data Science", 
            feed_url="https://towardsdatascience.com/feed"
        )