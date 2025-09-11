from .rss_base import RSSFeedScraper


class OpenAIBlogScraper(RSSFeedScraper):
    """
    Specialized RSS scraper dla OpenAI official blog (openai.com/blog).
    
    Implementuje scraping oficjalnych announcementów, research updates, i product releases
    z OpenAI. Jest to jeden z najważniejszych sourceów dla AI news, covering breakthrough
    research, model releases (GPT, DALL-E), i company announcements.
    
    Architektura:
    - Extends RSSFeedScraper: Inherits RSS parsing capabilities
    - Auto-discovery Compatible: Detected by ScraperFactory as "openai_blog"
    - Standard RSS Format: Uses OpenAI's official RSS feed
    - Template Method: Uses inherited scrape() workflow
    
    Content Characteristics:
    - High-quality, authoritative AI research content
    - Major model releases i technical breakthroughs
    - Company news i strategic announcements
    - Research paper releases i technical deep-dives
    
    Wykorzystywana przez:
    - NewsOrchestrationService batch scraping operations
    - Management commands dla OpenAI-specific updates
    - Automated news aggregation focusing na OpenAI developments
    - Research monitoring workflows
    
    RSS Feed Details:
    - Source: https://openai.com/blog/rss/
    - Format: Standard RSS 2.0
    - Update frequency: Irregular (major announcements)
    - Content quality: Very high (primary source)
    
    Auto-discovery Registration:
    - Factory name: "openai_blog"
    - Class name: "OpenAIBlogScraper"
    - File: openai_blog_scraper.py
    
    Example Usage:
    python manage.py scrape_news --source openai_blog
    
    Content Examples:
    - "Introducing GPT-4" - Major model releases
    - "Research Updates" - Technical breakthroughs
    - "Safety and Alignment" - AI safety research
    - "Product Updates" - ChatGPT, API improvements
    """
    
    def __init__(self):
        """
        Inicjalizuje OpenAIBlogScraper z official OpenAI RSS feed configuration.
        
        Configures scraper dla OpenAI official blog z proper source identification
        i RSS feed URL. Inherits all RSS parsing capabilities z RSSFeedScraper.
        
        Configuration:
        - source_name: "OpenAI Blog" - czytelna nazwa dla database storage
        - feed_url: "https://openai.com/blog/rss/" - official RSS endpoint
        
        Inheritance:
        - Inherits HTTP session management z BaseScraper
        - Inherits RSS parsing logic z RSSFeedScraper
        - Inherits error handling i recovery mechanisms
        
        Auto-discovery:
        - Automatically registered przez ScraperFactory as "openai_blog"
        - Available dla batch operations i targeted scraping
        """
        # Initialize parent RSSFeedScraper z OpenAI-specific configuration
        super().__init__(
            source_name="OpenAI Blog",              # Database source identifier
            feed_url="https://openai.com/blog/rss/" # Official OpenAI RSS endpoint
        )