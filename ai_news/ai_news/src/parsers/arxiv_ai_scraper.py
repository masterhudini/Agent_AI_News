from .rss_base import RSSFeedScraper
from typing import List
import logging
from .base import NewsArticleData

logger = logging.getLogger(__name__)


class ArxivAIScraper(RSSFeedScraper):
    """Scraper for arXiv cs.AI category RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="arXiv AI", 
            feed_url="https://export.arxiv.org/rss/cs.AI"
        )
    
    def _extract_content(self, entry) -> str:
        """Override to handle arXiv-specific content format"""
        # arXiv RSS feeds have abstracts in summary field
        content_fields = ['summary', 'description', 'content']
        
        for field in content_fields:
            content = entry.get(field, '')
            if content:
                if isinstance(content, list) and content:
                    content = content[0].get('value', '') if isinstance(content[0], dict) else str(content[0])
                elif isinstance(content, dict):
                    content = content.get('value', '')
                
                # Clean arXiv-specific formatting
                content = str(content)
                # Remove common arXiv prefixes
                if content.startswith('arXiv:'):
                    content = content.split('\n', 1)[-1] if '\n' in content else content
                
                content = self._clean_text(content)
                if content:
                    return content
        
        return ""