from .rss_base import RSSFeedScraper


class ScienceDailyAIScraper(RSSFeedScraper):
    """Scraper for ScienceDaily AI RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="ScienceDaily AI", 
            feed_url="https://www.sciencedaily.com/rss/computers_math/artificial_intelligence.xml"
        )