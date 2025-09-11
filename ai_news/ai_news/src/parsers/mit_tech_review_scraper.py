from .rss_base import RSSFeedScraper


class MITTechReviewScraper(RSSFeedScraper):
    """Scraper for MIT Technology Review RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="MIT Technology Review", 
            feed_url="https://www.technologyreview.com/feed/"
        )