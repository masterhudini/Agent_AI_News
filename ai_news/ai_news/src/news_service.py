from typing import List, Dict, Optional
import logging
from datetime import datetime
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


class NewsOrchestrationService:
    """
    Główny orchestrator dla całego systemu scraping'u, deduplication i summarization newsów.
    
    Jest to centralny service łączący wszystkie komponenty systemu w spojón workflow.
    Koordinuje scraping z multiple sources, deduplication, AI-powered summarization
    i provides unified API dla wszystkich news operations.
    
    Architektura:
    - Service Layer Pattern: High-level API dla complex operations
    - Dependency Injection: Komponenty injected dla loose coupling
    - Transaction Management: Atomic operations dla data integrity
    - Error Orchestration: Centralized error handling i recovery
    
    Core Components:
    - DuplicationService: Hash + semantic deduplication using OpenAI + Qdrant
    - BlogSummaryService: AI-powered blog generation using LangChain
    - LangChainNewsOrchestrator: Advanced AI operations i analysis
    - ScraperFactory: Auto-discovery i management parserów
    
    Wykorzystywana przez:
    - Management commands (scrape_news, langchain_analysis)
    - Django admin interfaces
    - API endpoints dla external integrations
    - Scheduled tasks i cron jobs
    - Development i testing workflows
    
    Key Operations:
    - Full pipeline scraping (all sources)
    - Single source targeted scraping
    - Daily/weekly AI-powered summaries
    - Article analysis i insights
    - Interactive querying through conversational AI
    - Database cleanup i maintenance
    
    Performance Considerations:
    - Batch processing dla scalability
    - Atomic transactions dla data integrity
    - Graceful error handling dla reliability
    - Configurable AI models dla cost optimization
    """
    
    def __init__(self, 
                 embedding_model: str = "text-embedding-3-small",
                 llm_model: str = "gpt-4o-mini",
                 temperature: float = 0.7,
                 deduplication_service=None,
                 blog_summary_service=None,
                 langchain_orchestrator=None):
        """
        Inicjalizuje NewsOrchestrationService z dependency injection support.
        
        Creates unified service integrating scraping, deduplication, i AI capabilities.
        Supports both traditional initialization and dependency injection.
        
        Args:
            embedding_model: OpenAI embedding model dla semantic deduplication
                           (default "text-embedding-3-small" - cost effective)
            llm_model: OpenAI LLM model dla summarization i analysis
                      (default "gpt-4o-mini" - balanced performance/cost)
            temperature: AI creativity level 0.0-1.0 (default 0.7)
                        Balanced setting dla engaging ale consistent content
            deduplication_service: Injected deduplication service (optional)
            blog_summary_service: Injected blog summary service (optional)
            langchain_orchestrator: Injected LangChain orchestrator (optional)
        
        Initialized Services:
        - DuplicationService: Uses embedding_model dla vector similarity
        - BlogSummaryService: Uses llm_model + temperature dla content generation
        - LangChainNewsOrchestrator: Comprehensive AI operations
        
        Architecture Notes:
        - Supports dependency injection for testability
        - Falls back to direct instantiation if no dependencies injected
        - Only LangChain services - no fallback models dla consistency
        """
        
        # Use injected dependencies or create new instances
        if deduplication_service is not None:
            self.duplication_service = deduplication_service
        else:
            from .deduplication import DuplicationService
            self.duplication_service = DuplicationService(model=embedding_model)
            
        if blog_summary_service is not None:
            self.blog_summary_service = blog_summary_service
        else:
            from .summarization import BlogSummaryService
            self.blog_summary_service = BlogSummaryService(model=llm_model, temperature=temperature)
            
        if langchain_orchestrator is not None:
            self.langchain_orchestrator = langchain_orchestrator
        else:
            from .langchain_chains import LangChainNewsOrchestrator
            self.langchain_orchestrator = LangChainNewsOrchestrator(model_type="openai")
    
    def scrape_all_sources(self) -> Dict[str, int]:
        """
        Orchestrates scraping ze wszystkich available sources w batch operation.
        
        Iterates przez wszystkie registered scrapers, executes scraping dla każdego,
        i aggregates results. Provides comprehensive coverage wszystkich news sources
        w single operation.
        
        Workflow:
        1. Get lista wszystkich available scrapers z Factory
        2. Iterate przez każdy scraper sequentially
        3. Execute scraping z error isolation
        4. Aggregate results i statistics
        5. Return comprehensive summary
        
        Wykorzystywana przez:
        - Management command scrape_news --all
        - Scheduled batch processing tasks
        - Full system refresh operations
        - Development i testing workflows
        
        Returns:
            Dict[str, int]: Mapping scraper_name -> articles_count
                           Pokazuje ile unique articles scraped z każdego source
                           0 dla sources z errors
                           
        Error Handling:
            Individual scraper failures nie stop batch process
            Failed scrapers logged i marked z 0 count
            Comprehensive logging dla monitoring
            
        Performance:
            Sequential processing - nie parallel dla stability
            Each scraper isolated w try/catch dla error recovery
        """
        from .parsers import ScraperFactory
        
        results = {}
        # Get wszystkie available scrapers z auto-discovery
        available_scrapers = ScraperFactory.get_available_scrapers()
        
        logger.info(f"Starting scraping process for {len(available_scrapers)} sources")
        
        # Process każdy scraper individually z error isolation
        for scraper_name in available_scrapers:
            try:
                # Execute single source scraping z deduplication
                count = self.scrape_single_source(scraper_name)
                results[scraper_name] = count
                logger.info(f"Scraped {count} articles from {scraper_name}")
            except Exception as e:
                # Individual scraper failure nie crashes batch process
                logger.error(f"Error scraping {scraper_name}: {e}")
                results[scraper_name] = 0
        
        # Calculate i log aggregate statistics
        total_articles = sum(results.values())
        logger.info(f"Total articles scraped: {total_articles}")
        
        return results
    
    def scrape_single_source(self, scraper_name: str) -> int:
        """
        Scrapes articles z single specified source z complete processing pipeline.
        
        Executes full workflow dla single source: scraping → deduplication → storage.
        Each article jest processed through deduplication engine i stored w database.
        
        Workflow:
        1. Create scraper instance z Factory
        2. Execute scraping dla raw article data
        3. Process każdy article individually
        4. Check URL-based duplicates (fast path)
        5. Create NewsArticle object w database
        6. Run deduplication pipeline (hash + semantic)
        7. Count unique articles added
        
        Wykorzystywana przez:
        - scrape_all_sources() dla batch processing
        - Management command scrape_news --source
        - Targeted source refresh operations
        - Development i testing
        
        Args:
            scraper_name: Name registered scraper (case-insensitive)
                         Must be available w ScraperFactory registry
                         
        Returns:
            int: Number unique (non-duplicate) articles added
                0 jeśli source failed lub no new articles
                
        Database Operations:
        - Atomic transactions dla each article
        - URL-based duplicate checking dla fast path
        - Automatic content_hash generation
        - Deduplication processing dla semantic similarity
        
        Error Handling:
            Individual article failures logged ale nie stop processing
            Database rollback dla failed transactions
            Graceful recovery z malformed article data
        """
        from .parsers import ScraperFactory
        from ..models import NewsArticle
        
        try:
            # Create scraper instance z Factory (auto-discovery)
            scraper = ScraperFactory.create_scraper(scraper_name)
            # Execute scraping dla raw article data
            articles_data = scraper.scrape()
            
            new_articles_count = 0
            
            # Process każdy article individually z error isolation
            for article_data in articles_data:
                try:
                    # Use atomic transaction dla data integrity
                    with transaction.atomic():
                        # Fast path: check URL-based duplicates first
                        if NewsArticle.objects.filter(url=article_data.url).exists():
                            continue  # Skip existing articles
                        
                        # Create new NewsArticle object
                        article = NewsArticle(
                            title=article_data.title[:500],  # Truncate dla DB constraints
                            content=article_data.content,
                            url=article_data.url,
                            source=article_data.source,
                            published_date=article_data.published_date or timezone.now(),
                        )
                        article.save()  # Triggers automatic content_hash generation
                        
                        # Run comprehensive deduplication pipeline
                        # Includes hash-based + semantic similarity detection
                        is_duplicate = self.duplication_service.process_article_for_duplicates(article)
                        
                        # Count only truly unique articles
                        if not is_duplicate:
                            new_articles_count += 1
                        
                        logger.debug(f"Processed article: {article.title}")
                
                except Exception as e:
                    # Log individual article failures ale continue processing
                    logger.error(f"Error processing article {article_data.title}: {e}")
                    continue
            
            return new_articles_count
        
        except Exception as e:
            # Handle scraper-level failures gracefully
            logger.error(f"Error in scrape_single_source for {scraper_name}: {e}")
            return 0
    
    def generate_daily_summary(self, topic_category: str = "AI News") -> Optional:
        """
        Generates AI-powered daily summary z articles published w last 24 hours.
        
        Uses BlogSummaryService do tworzenia comprehensive daily blog post
        z recent articles. Filters unique articles i creates engaging summary.
        
        Wykorzystywana przez:
        - run_full_pipeline() jako part of complete workflow
        - Management commands dla daily summary generation
        - Scheduled tasks dla automated daily reports
        - API endpoints dla on-demand daily content
        
        Args:
            topic_category: Category dla summary context (default "AI News")
                           Used by AI dla appropriate tone i focus
                           
        Returns:
            Optional[BlogSummary]: Generated daily summary object
                                  None jeśli no articles lub generation failed
                                  
        Process:
        1. BlogSummaryService queries last 24h articles
        2. Filters unique articles (is_duplicate=False)
        3. AI generates comprehensive blog post
        4. Creates BlogSummary object w database
        5. Associates articles z summary
        
        Error Handling:
            Logs errors ale returns None instead of crashing
            Graceful degradation dla service reliability
        """
        try:
            # Delegate to BlogSummaryService dla AI-powered generation
            summary = self.blog_summary_service.create_daily_summary(topic_category)
            if summary:
                logger.info(f"Generated daily summary: {summary.title}")
            return summary
        except Exception as e:
            # Graceful error handling - log ale nie crash system
            logger.error(f"Error generating daily summary: {e}")
            return None
    
    def generate_weekly_summary(self, topic_category: str = "AI News") -> Optional:
        """
        Generates AI-powered weekly summary z articles published w last 7 days.
        
        Creates comprehensive weekly overview covering major trends i developments.
        More extensive than daily summaries - broader perspective na week's events.
        
        Wykorzystywana przez:
        - run_full_pipeline() dla complete reporting
        - Weekly scheduled tasks dla retrospective analysis
        - Management commands z --weekly flag
        - Newsletter generation systems
        
        Args:
            topic_category: Category dla summary context (default "AI News")
                           Guides AI focus i tone dla appropriate audience
                           
        Returns:
            Optional[BlogSummary]: Generated weekly summary object
                                  None jeśli no articles lub generation failed
                                  
        Characteristics:
        - 7-day article window (more comprehensive than daily)
        - Trend analysis i pattern recognition
        - Higher-level insights i synthesis
        - Archive-quality content dla historical reference
        
        Error Handling:
            Graceful failure handling z comprehensive logging
            Returns None ale nie disrupts calling workflows
        """
        try:
            # Delegate to BlogSummaryService dla comprehensive weekly analysis
            summary = self.blog_summary_service.create_weekly_summary(topic_category)
            if summary:
                logger.info(f"Generated weekly summary: {summary.title}")
            return summary
        except Exception as e:
            # Graceful error handling z detailed logging
            logger.error(f"Error generating weekly summary: {e}")
            return None
    
    def run_full_pipeline(self, generate_summary: bool = True) -> Dict:
        """
        Executes complete end-to-end news processing pipeline.
        
        Comprehensive operation combining scraping, deduplication, i summarization
        w single workflow. Provides complete system refresh z optional AI summaries.
        
        Pipeline Stages:
        1. Scrape wszystkie available sources
        2. Process articles through deduplication
        3. Calculate database statistics
        4. Generate AI-powered summaries (optional)
        5. Return comprehensive results
        
        Wykorzystywana przez:
        - Management command scrape_news --all --generate-summary
        - Scheduled complete system refresh tasks
        - Admin operations dla full data processing
        - Integration tests dla end-to-end validation
        
        Args:
            generate_summary: Whether to create AI summaries (default True)
                             Can be disabled dla faster processing
                             
        Returns:
            Dict: Comprehensive results containing:
                 - 'scraping_results': Per-source article counts
                 - 'daily_summary': BlogSummary object lub None
                 - 'weekly_summary': BlogSummary object lub None
                 - 'total_unique_articles': Database count unique articles
                 - 'total_duplicates': Database count duplicate articles
                 
        Error Resilience:
            Pipeline continues even jeśli individual stages fail
            Partial results returned dla debugging i monitoring
            Comprehensive logging dla operational visibility
            
        Performance:
            Sequential execution dla stability
            Optional summary generation dla faster basic processing
            Database queries optimized dla statistics calculation
        """
        from ..models import NewsArticle
        
        # Initialize comprehensive results structure
        results = {
            'scraping_results': {},      # Per-source article counts
            'daily_summary': None,       # BlogSummary object
            'weekly_summary': None,      # BlogSummary object
            'total_unique_articles': 0,  # Database statistics
            'total_duplicates': 0        # Database statistics
        }
        
        try:
            # STAGE 1: Comprehensive source scraping
            logger.info("Starting full news pipeline")
            results['scraping_results'] = self.scrape_all_sources()
            
            # STAGE 2: Calculate database statistics
            # Optimized queries dla performance
            results['total_unique_articles'] = NewsArticle.objects.filter(is_duplicate=False).count()
            results['total_duplicates'] = NewsArticle.objects.filter(is_duplicate=True).count()
            
            # STAGE 3: AI-powered content generation (optional)
            if generate_summary:
                results['daily_summary'] = self.generate_daily_summary()
                results['weekly_summary'] = self.generate_weekly_summary()
            
            logger.info("Full news pipeline completed successfully")
            
        except Exception as e:
            # Pipeline-level error handling - return partial results
            logger.error(f"Error in full pipeline: {e}")
        
        return results
    
    def get_latest_articles(self, limit: int = 50, unique_only: bool = True) -> List:
        """
        Retrieves lista most recently published articles z database.
        
        Utility method dla getting latest articles z flexible filtering options.
        Supports both unique articles i complete dataset depending na use case.
        
        Wykorzystywana przez:
        - API endpoints dla recent articles display
        - Admin interfaces dla content review
        - Testing i development workflows
        - Analytics i reporting systems
        
        Args:
            limit: Maximum number articles to return (default 50)
                  Controls pagination i performance
            unique_only: Filter only unique articles (default True)
                        True = only non-duplicates, False = all articles
                        
        Returns:
            List[NewsArticle]: Ordered lista articles (newest first)
                              Empty list jeśli no articles found
                              
        Query Optimization:
            Uses Django ORM ordering dla efficient database query
            Applies is_duplicate filter conditionally
            Limits result set dla memory efficiency
        
        Performance:
            Database query optimized z proper indexing
            Limit parameter prevents large result sets
            Order by published_date dla chronological sorting
        """
        from ..models import NewsArticle
        
        # Start z base queryset
        queryset = NewsArticle.objects.all()
        
        # Apply unique filter conditionally
        if unique_only:
            queryset = queryset.filter(is_duplicate=False)
        
        # Order by date (newest first) i apply limit
        return list(queryset.order_by('-published_date')[:limit])
    
    def get_articles_by_source(self, source: str, limit: int = 20) -> List:
        """
        Retrieves articles z specific news source w chronological order.
        
        Filtered query dla getting articles z particular source (np. "OpenAI Blog").
        Automatically filters unique articles i orders by publication date.
        
        Wykorzystywana przez:
        - Source-specific analysis workflows
        - API endpoints dla source filtering
        - Admin interfaces dla source management
        - Quality analysis i source evaluation
        
        Args:
            source: Exact source name (case-sensitive)
                   Must match NewsArticle.source field exactly
            limit: Maximum articles to return (default 20)
                  Reasonable default dla source-specific queries
                  
        Returns:
            List[NewsArticle]: Articles z specified source (newest first)
                              Only unique articles (is_duplicate=False)
                              Empty list jeśli source nie found
                              
        Query Details:
            Filters by exact source match i unique status
            Orders by published_date descending
            Applies limit dla performance
            
        Use Cases:
            Source quality analysis, content curation,
            debugging source-specific issues
        """
        from ..models import NewsArticle
        
        # Query articles z specific source
        return list(
            NewsArticle.objects.filter(
                source=source,              # Exact source match
                is_duplicate=False          # Only unique articles
            ).order_by('-published_date')[:limit]  # Newest first, limited
        )
    
    def get_statistics(self) -> Dict:
        """
        Generates comprehensive statistics about system state i performance.
        
        Comprehensive analytics method providing detailed insights into database
        content, source performance, deduplication efficiency, i system health.
        
        Wykorzystywana przez:
        - Management commands dla system monitoring
        - Admin dashboards dla operational visibility
        - API endpoints dla integration monitoring
        - Performance analysis i optimization
        
        Statistics Provided:
        - Total article count (all articles w database)
        - Unique article count (after deduplication)
        - Duplicate count i percentage
        - Per-source detailed statistics
        - Available scraper count
        - Generated summaries count
        
        Returns:
            Dict: Comprehensive statistics containing:
                 - 'total_articles': Total articles w database
                 - 'unique_articles': Non-duplicate articles count
                 - 'duplicates': Duplicate articles count
                 - 'duplicate_rate': Percentage duplicates detected
                 - 'source_statistics': Per-source breakdown
                 - 'available_scrapers': Lista registered scrapers
                 - 'total_summaries': BlogSummary count
                 
        Performance:
            Multiple optimized database queries
            Source statistics calculated efficiently
            Cached scraper list z Factory
        """
        from ..models import NewsArticle, BlogSummary
        from .parsers import ScraperFactory
        
        # Core database statistics
        total_articles = NewsArticle.objects.count()
        unique_articles = NewsArticle.objects.filter(is_duplicate=False).count()
        duplicates = NewsArticle.objects.filter(is_duplicate=True).count()
        
        # Per-source detailed statistics
        source_stats = {}
        for source in NewsArticle.objects.values_list('source', flat=True).distinct():
            source_stats[source] = {
                'total': NewsArticle.objects.filter(source=source).count(),
                'unique': NewsArticle.objects.filter(source=source, is_duplicate=False).count()
            }
        
        # Comprehensive system statistics
        return {
            'total_articles': total_articles,           # All articles w database
            'unique_articles': unique_articles,         # After deduplication
            'duplicates': duplicates,                   # Detected duplicates
            'duplicate_rate': (duplicates / total_articles * 100) if total_articles > 0 else 0,  # Efficiency %
            'source_statistics': source_stats,          # Per-source breakdown
            'available_scrapers': ScraperFactory.get_available_scrapers(),  # Active scrapers
            'total_summaries': BlogSummary.objects.count()  # Generated content
        }
    
    def cleanup_old_articles(self, days: int = 30) -> int:
        """
        Performs maintenance cleanup removing old articles i associated data.
        
        Database maintenance operation dla removing articles older than specified
        threshold. Includes cleanup z vector database dla complete removal.
        
        Workflow:
        1. Calculate cutoff date based na days parameter
        2. Query old articles based na scraped_date
        3. Remove articles z vector index (Qdrant)
        4. Delete articles z main database
        5. Return count removed articles
        
        Wykorzystywana przez:
        - Scheduled maintenance tasks
        - Storage management operations
        - Database optimization workflows
        - Development cleanup procedures
        
        Args:
            days: Age threshold w days (default 30)
                 Articles older than this będą removed
                 
        Returns:
            int: Number articles removed
                0 jeśli no old articles found
                
        Safety Features:
            Vector index cleanup before database deletion
            Error handling dla partial failures
            Comprehensive logging dla audit trail
            
        Performance:
            Batch deletion dla efficiency
            Date-based query optimization
            Two-phase cleanup dla data integrity
            
        Warning:
            Destructive operation - permanently removes articles
            Should be used carefully w production environments
        """
        from datetime import timedelta
        from ..models import NewsArticle
        
        # Calculate cutoff date dla cleanup threshold
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Query old articles based na scraped_date
        old_articles = NewsArticle.objects.filter(scraped_date__lt=cutoff_date)
        count = old_articles.count()
        
        # PHASE 1: Remove z vector index first (data consistency)
        for article in old_articles:
            try:
                # Clean vector database dla complete removal
                self.duplication_service.vector_deduplicator.remove_article_from_index(article.id)
            except Exception as e:
                # Log individual failures ale continue cleanup
                logger.error(f"Error removing article {article.id} from vector index: {e}")
        
        # PHASE 2: Delete articles z main database
        old_articles.delete()
        
        logger.info(f"Cleaned up {count} old articles")
        return count
    
    def create_intelligent_blog_summary(self, topic_category: str = "AI News") -> Optional:
        """
        Creates sophisticated blog summary using advanced LangChain AI analysis.
        
        Premium content generation method combining article analysis z structured
        blog post generation. Two-stage AI process: analysis then synthesis.
        
        Advanced Features:
        - Individual article analysis z NewsAnalyzer
        - Structured blog generation z BlogGenerator
        - Combined insights synthesis
        - Professional formatting i structure
        
        Process:
        1. Query last 24h unique articles
        2. LangChain analysis dla structured insights
        3. AI blog generation combining all insights
        4. Parse structured result (title, intro, content, conclusion)
        5. Create BlogSummary object w database
        6. Associate articles z summary
        
        Wykorzystywana przez:
        - Premium content generation workflows
        - High-quality editorial processes
        - API endpoints dla advanced summaries
        - Scheduled premium content tasks
        
        Args:
            topic_category: Topic context dla AI generation
                           Guides analysis focus i writing style
                           
        Returns:
            Optional[BlogSummary]: Advanced blog summary object
                                  None jeśli no articles lub AI generation failed
                                  
        Quality Features:
        - Multi-stage AI processing dla higher quality
        - Structured output parsing dla consistent format
        - Comprehensive error handling
        - Professional content standards
        """
        try:
            from ..models import NewsArticle
            from datetime import timedelta
            
            # Query last 24h unique articles dla intelligent analysis
            yesterday = datetime.now() - timedelta(days=1)
            articles = list(NewsArticle.objects.filter(
                is_duplicate=False,              # Only unique articles
                published_date__gte=yesterday,           # From yesterday
                published_date__lt=datetime.now()        # Until now
            ).order_by('-published_date'))    # Newest first
            
            if not articles:
                logger.info("No new articles found for intelligent summary")
                return None
            
            # STAGE 1: Advanced LangChain AI processing
            # Two-stage process: analysis → generation → synthesis
            result = self.langchain_orchestrator.create_intelligent_blog_post(topic_category, articles)
            
            if "error" in result:
                logger.error(f"Error in intelligent blog generation: {result['error']}")
                return None
            
            # STAGE 2: Parse structured AI result i create database entry
            from ..models import BlogSummary
            blog_structure = result["blog_post"]
            
            # Create comprehensive BlogSummary z structured content
            blog_summary = BlogSummary.objects.create(
                title=blog_structure["title"],  # AI-generated compelling title
                # Combine structured sections into complete summary
                summary=f"{blog_structure['introduction']}\n\n{blog_structure['main_content']}\n\n{blog_structure['conclusion']}",
                topic_category=topic_category
            )
            
            # Associate all analyzed articles z the summary
            blog_summary.articles.set(articles)
            
            logger.info(f"Created intelligent blog summary: {blog_summary.title}")
            return blog_summary
            
        except Exception as e:
            # Comprehensive error handling dla premium feature
            logger.error(f"Error creating intelligent blog summary: {e}")
            return None
    
    def search_similar_articles(self, query: str, limit: int = 5) -> List:
        """
        Semantic search dla articles similar to natural language query.
        
        Vector-based similarity search using OpenAI embeddings i Qdrant database.
        Finds articles semantically related do user's query, nie just keyword matches.
        
        Wykorzystywana przez:
        - Interactive query interfaces
        - Research workflows
        - Content discovery systems
        - API endpoints dla article search
        
        Args:
            query: Natural language search query
                  Can be question, topic, lub description
            limit: Maximum articles to return (default 5)
                  Controls result size dla performance
                  
        Returns:
            List[NewsArticle]: Articles semantically similar to query
                              Ordered by similarity score (highest first)
                              Empty list jeśli no matches above threshold
                              
        Technology:
        - OpenAI text-embedding-3-small dla query encoding
        - Qdrant vector database dla similarity search
        - Configurable similarity threshold (default 85%)
        - LangChain integration dla seamless operation
        
        Performance:
        - Sub-second response dla millions of articles
        - Vector search optimized dla speed
        - Limited result sets dla efficiency
        """
        try:
            # Delegate to DuplicationService vector search capabilities
            return self.duplication_service.search_similar_content(query, limit)
        except Exception as e:
            # Graceful error handling dla search functionality
            logger.error(f"Error searching similar articles: {e}")
            return []
    
    def analyze_articles_with_langchain(self, articles: List) -> List[Dict]:
        """
        Performs comprehensive AI-powered analysis na provided articles.
        
        Advanced analytics method using LangChain NewsAnalyzer dla structured
        insights extraction. Provides detailed analysis including topics,
        importance scoring, categorization, i summarization.
        
        Wykorzystywana przez:
        - Research workflows requiring detailed analysis
        - Content curation systems
        - Editorial processes
        - API endpoints dla article insights
        
        Args:
            articles: Lista NewsArticle objects dla analysis
                     No limit - processes wszystkie provided articles
                     
        Returns:
            List[Dict]: Lista analysis results, każdy containing:
                       - 'article': Original NewsArticle object
                       - 'analysis': Structured insights (topics, importance, category, summary)
                       - 'processed_at': Processing timestamp
                       
        Analysis Features:
        - Key topic extraction
        - Importance scoring (0.0-1.0)
        - Category classification
        - Automated summarization
        - Structured output format
        
        Error Handling:
        - Individual article failures logged ale nie stop batch
        - Graceful degradation dla partial results
        - Empty list returned on complete failure
        """
        try:
            # Delegate to LangChainNewsOrchestrator dla comprehensive analysis
            return self.langchain_orchestrator.process_articles_with_analysis(articles)
        except Exception as e:
            # Error handling z fallback to empty results
            logger.error(f"Error analyzing articles with LangChain: {e}")
            return []
    
    def interactive_news_query(self, query: str) -> str:
        """
        Handles interactive conversational queries about news database using AI agent.
        
        Natural language interface dla exploring news data. AI agent analyzes
        user queries, selects appropriate tools, i provides comprehensive responses.
        
        Agent Capabilities:
        - Semantic article search using vector database
        - Database statistics i metrics
        - Topic-based trend analysis
        - Multi-step reasoning dla complex queries
        
        Wykorzystywana przez:
        - Interactive CLI tools
        - Chat interfaces dla news exploration
        - Research workflows
        - API endpoints dla conversational search
        
        Args:
            query: Natural language question about news data
                  Examples: "Find articles about machine learning",
                           "What are the latest AI trends?",
                           "Show me database statistics"
                           
        Returns:
            str: Comprehensive response based na query analysis
                Agent uses available tools to answer question
                Error message jeśli processing fails
                
        AI Agent Features:
        - OpenAI Functions dla reliable tool calling
        - Context-aware responses
        - Multi-step reasoning capabilities
        - Error recovery i graceful degradation
        """
        try:
            # Delegate to LangChainNewsOrchestrator agent capabilities
            return self.langchain_orchestrator.interactive_news_query(query)
        except Exception as e:
            # User-friendly error handling dla interactive queries
            logger.error(f"Error processing interactive query: {e}")
            return f"Sorry, I encountered an error processing your query: {e}"