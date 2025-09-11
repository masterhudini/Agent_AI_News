from .rss_base import RSSFeedScraper
from typing import List
import logging
from .base import NewsArticleData

logger = logging.getLogger(__name__)


class RedditMachineLeaningScraper(RSSFeedScraper):
    """Scraper for Reddit r/MachineLearning RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="Reddit ML", 
            feed_url="https://www.reddit.com/r/MachineLearning/.rss"
        )
    
    def _extract_content(self, entry) -> str:
        """Override to handle Reddit-specific content format"""
        # Reddit RSS feeds often have content in different fields
        content_fields = ['content', 'summary', 'description']
        
        for field in content_fields:
            content = entry.get(field, '')
            if content:
                # Handle Reddit HTML content
                if isinstance(content, list) and content:
                    content = content[0].get('value', '') if isinstance(content[0], dict) else str(content[0])
                elif isinstance(content, dict):
                    content = content.get('value', '')
                
                # Clean Reddit-specific formatting
                content = str(content)
                content = content.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                
                # Remove HTML tags but keep the text
                from bs4 import BeautifulSoup
                try:
                    soup = BeautifulSoup(content, 'html.parser')
                    content = soup.get_text()
                except:
                    pass
                
                content = self._clean_text(content)
                if content:
                    return content
        
        return ""