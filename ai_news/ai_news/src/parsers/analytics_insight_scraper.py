from .rss_base import RSSFeedScraper


class AnalyticsInsightScraper(RSSFeedScraper):
    """Scraper for Analytics Insight RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="Analytics Insight", 
            feed_url="https://www.analyticsinsight.net/feed/"
        )