from typing import List
from datetime import datetime
import logging
import time
from .base import BaseScraper, NewsArticleData
from ..security import RateLimiter

logger = logging.getLogger(__name__)


class HackerNewsScraper(BaseScraper):
    """
    Specialized API-based scraper dla Hacker News (news.ycombinator.com).
    
    Implementuje scraping z Hacker News Firebase API dla top stories.
    Different from RSS scrapers - uses RESTful API dla structured data access.
    Focuses on tech news, startup stories, i programming-related content.
    
    Architektura:
    - Extends BaseScraper: Direct inheritance (nie RSSFeedScraper)
    - API-based: Uses Firebase API endpoints
    - Two-stage Process: Get story IDs → fetch individual stories
    - Auto-discovery Compatible: Detected by ScraperFactory as "hackernews"
    
    API Details:
    - Base URL: https://hacker-news.firebaseio.com/v0
    - Top Stories: /topstories.json (returns array of story IDs)
    - Individual Story: /item/{id}.json (returns story details)
    - Rate Limits: Reasonable limits dla public API
    
    Content Characteristics:
    - Tech-focused news i discussions
    - High-quality curated content
    - Strong programming i startup focus
    - Community-driven story selection
    
    Wykorzystywana przez:
    - NewsOrchestrationService dla tech news aggregation
    - Management commands targeting HN content
    - Automated monitoring programming trends
    - Research workflows dla tech industry insights
    
    Performance Considerations:
    - Limited to 30 stories (max_stories) dla API efficiency
    - Individual API calls dla each story (necessary due to API design)
    - Timeout handling dla network reliability
    - Error isolation - failed stories don't crash entire operation
    
    Content Filtering:
    - Only processes 'story' type (excludes Ask HN, polls)
    - Requires URL - focuses na external content (nie discussions)
    - Validates title presence dla quality control
    
    Auto-discovery Registration:
    - Factory name: "hackernews"
    - Class name: "HackerNewsScraper"
    - File: hackernews_scraper.py
    """
    
    def __init__(self):
        """
        Inicjalizuje HackerNewsScraper z API configuration i limits.
        
        Sets up scraper dla Hacker News Firebase API z proper rate limiting
        i endpoint configuration. Inherits HTTP session z BaseScraper.
        
        Configuration:
        - source_name: "Hacker News" dla database identification
        - api_url: Firebase API base URL
        - max_stories: 30 stories limit dla performance i politeness
        
        API Architecture:
        - Firebase backend provides JSON endpoints
        - Two-stage process: story IDs then individual stories
        - No authentication required dla public access
        
        Performance Settings:
        - 30 stories max balances coverage z API efficiency
        - Individual timeouts dla network reliability
        - Error isolation prevents cascade failures
        """
        # Initialize parent BaseScraper z source identification
        super().__init__("Hacker News")
        
        # Firebase API configuration
        self.api_url = "https://hacker-news.firebaseio.com/v0"  # Official API endpoint
        self.max_stories = 30  # Balance coverage z API politeness
        
        # Rate limiting dla API protection (10 requests per minute)
        self.rate_limiter = RateLimiter(max_requests=10, time_window=60)
    
    def scrape(self) -> List[NewsArticleData]:
        """
        Scrapes top stories z Hacker News using two-stage API process.
        
        Implements efficient API-based scraping workflow:
        1. Fetch top story IDs z /topstories.json endpoint
        2. Iterate through IDs i fetch individual story details
        3. Filter stories based na type, URL presence, i title
        4. Convert API response to NewsArticleData format
        
        Returns:
            List[NewsArticleData]: Processed Hacker News stories
                                  Filtered dla external links only
                                  Limited to max_stories count
                                  
        API Workflow:
        - GET /topstories.json → array of story IDs
        - For each ID: GET /item/{id}.json → story details
        - Filter: type='story', has URL, has title
        - Transform: API format → NewsArticleData
        
        Error Handling:
        - Individual story failures logged ale don't stop process
        - Network timeouts handled gracefully
        - API rate limiting respected through reasonable delays
        - Empty result returned na complete failure
        
        Content Quality:
        - Excludes Ask HN, Show HN discussions (focuses na external links)
        - Requires title dla basic quality control
        - Includes author information when available
        - Uses timestamp dla accurate publish dates
        """
        articles = []
        
        try:
            logger.info(f"Starting Hacker News API scraping: {self.api_url}")
            
            # STAGE 1: Get top story IDs z Firebase API
            logger.info("Fetching top story IDs...")
            response = self.session.get(
                f"{self.api_url}/topstories.json", 
                timeout=10  # Network timeout dla reliability
            )
            response.raise_for_status()  # Raise exception dla HTTP errors
            
            # Limit to max_stories dla performance i API politeness
            story_ids = response.json()[:self.max_stories]
            logger.info(f"Retrieved {len(story_ids)} story IDs from top stories")
            
            # STAGE 2: Fetch individual story details
            logger.info(f"Processing {len(story_ids)} individual stories...")
            for story_id in story_ids:
                try:
                    # SECURITY: Rate limiting protection
                    if not self.rate_limiter.is_allowed():
                        wait_time = self.rate_limiter.wait_time()
                        logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s before next request")
                        time.sleep(wait_time)
                    
                    # Small delay between requests dla API politeness
                    time.sleep(0.1)  # 100ms delay
                    
                    # Fetch individual story data
                    story_response = self.session.get(
                        f"{self.api_url}/item/{story_id}.json",
                        timeout=10  # Per-story timeout
                    )
                    story_response.raise_for_status()
                    story = story_response.json()
                    
                    # Quality filtering: only external stories z URLs
                    # Excludes Ask HN, Show HN, polls, discussions
                    if (story.get('type') == 'story' and        # Must be story type
                        story.get('url') and                    # Must have external URL
                        story.get('title')):                   # Must have title
                        
                        # Convert API response to NewsArticleData format
                        article = NewsArticleData(
                            title=self._clean_text(story.get('title', '')),     # Clean title
                            content=self._clean_text(story.get('text', '')),     # Story text (often empty)
                            url=story.get('url', ''),                           # External link
                            source=self.source_name,                            # "Hacker News"
                            published_date=datetime.fromtimestamp(story.get('time', 0)),  # Unix timestamp
                            author=story.get('by', '')                          # HN username
                        )
                        articles.append(article)
                        
                except Exception as e:
                    # Individual story failure doesn't stop batch process
                    logger.error(f"Error processing Hacker News story {story_id}: {e}")
                    continue  # Skip failed story, continue z others
            
            logger.info(f"Successfully scraped {len(articles)} articles from Hacker News")
            
        except Exception as e:
            # Handle API-level failures gracefully
            logger.error(f"Error scraping Hacker News API: {e}")
        
        return articles