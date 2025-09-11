from typing import List
import feedparser  # Parsing RSS/Atom feeds
import logging
from .base import BaseScraper, NewsArticleData

# Logger dla RSS scraping operations
logger = logging.getLogger(__name__)


class RSSFeedScraper(BaseScraper):
    """
    Bazowa klasa dla wszystkich parserów RSS feeds.
    
    Implementuje wspólną logikę dla parsowania RSS i Atom feeds używając biblioteki feedparser.
    Obsługuje różne formaty RSS (RSS 2.0, RSS 1.0, Atom) i ekstraktuje content z różnych pól.
    
    Jest to klasa bazowa dla większości parserów w systemie - 30+ implementacji dziedziczy po niej.
    Zapewnia standardowe parsowanie RSS z intelligent content extraction i error handling.
    
    Architektura:
    - Template Method Pattern: definiuje workflow parsowania RSS
    - Strategy Pattern: _extract_content() może być override'owana przez subklasy
    - Error Recovery: graceful handling malformed feeds i missing fields
    - Content Intelligence: próbuje multiple fields do znalezienia treści
    
    Wykorzystywana przez:
    - OpenAIBlogScraper, GoogleAIBlogScraper, ArsTechnicaScraper (RSS feeds)
    - TechCrunchScraper, TheVergeScraper, WiredScraper (portal RSS)
    - BlogScraper implementations (academic i corporate blogs)
    
    Obsługuje formaty:
    - RSS 2.0 (najczęściej używany)
    - RSS 1.0/RDF (starszy format)
    - Atom feeds (nowoczesny standard)
    - Custom RSS variants z różnymi polami
    """
    
    def __init__(self, source_name: str, feed_url: str):
        """
        Inicjalizuje RSS scraper z nazwą źródła i URL feedu.
        
        Args:
            source_name: Czytelna nazwa źródła (np. "OpenAI Blog")
            feed_url: URL do RSS/Atom feed (np. "https://openai.com/blog/rss/")
        """
        super().__init__(source_name)  # Inicjalizuje BaseScraper (HTTP session etc.)
        self.feed_url = feed_url
    
    def scrape(self) -> List[NewsArticleData]:
        """
        Główna metoda parsowania RSS feed do listy NewsArticleData.
        
        Pobiera RSS feed, parsuje XML, ekstraktuje artykuły i konwertuje je
        na standardowy format NewsArticleData. Obsługuje błędy i malformed feeds.
        
        Workflow:
        1. Pobiera RSS feed przez HTTP (używa session z BaseScraper)
        2. Parsuje XML używając feedparser
        3. Iteruje przez entries w feed
        4. Dla każdego entry ekstraktuje: title, content, url, date, author
        5. Tworzy NewsArticleData objects
        6. Filtruje entries z brakującymi required fields (title, url)
        
        Returns:
            List[NewsArticleData]: Lista artykułów z RSS feed
                                  Może być pusta jeśli feed jest pusty lub invalid
        
        Note:
            Używa graceful error handling - pojedynczy broken entry nie crashuje całego feed'u.
            Loguje progress i błędy dla debugowania.
        """
        articles = []
        
        try:
            logger.info(f"Scraping RSS feed: {self.feed_url}")
            # feedparser.parse() obsługuje HTTP requests, caching i różne formaty RSS
            feed = feedparser.parse(self.feed_url)
            
            # Sprawdzamy czy feed ma entries - basic validation RSS format
            if not hasattr(feed, 'entries'):
                logger.error(f"Invalid RSS feed format: {self.feed_url}")
                return articles
            
            # Przetwarzamy każdy entry w RSS feed
            for entry in feed.entries:
                try:
                    # Ekstraktujemy kluczowe dane artykułu używając RSS fields
                    title = self._clean_text(entry.get('title', ''))           # <title>
                    content = self._extract_content(entry)                     # <description>/<content>
                    url = entry.get('link', '')                               # <link>
                    published_date = self._parse_date(entry.get('published', ''))  # <pubDate>
                    author = entry.get('author', '')                          # <author>
                    
                    # Minimum required fields validation
                    if title and url:  # Title i URL są wymagane dla deduplication
                        article = NewsArticleData(
                            title=title,
                            content=content,
                            url=url,
                            source=self.source_name,
                            published_date=published_date,
                            author=author
                        )
                        articles.append(article)
                        
                except Exception as e:
                    logger.error(f"Error processing RSS entry: {e}")
                    continue
                    
            logger.info(f"Successfully scraped {len(articles)} articles from {self.source_name}")
            
        except Exception as e:
            logger.error(f"Error scraping RSS feed {self.feed_url}: {e}")
        
        return articles
    
    def _extract_content(self, entry) -> str:
        """Extract content from RSS entry, trying multiple fields"""
        # Try different content fields in order of preference
        content_fields = ['content', 'summary', 'description']
        
        for field in content_fields:
            content = entry.get(field, '')
            if content:
                # Handle different content formats
                if isinstance(content, list) and content:
                    content = content[0].get('value', '') if isinstance(content[0], dict) else str(content[0])
                elif isinstance(content, dict):
                    content = content.get('value', '')
                
                content = self._clean_text(str(content))
                if content:
                    return content
        
        return ""