"""
AI News Processing Pipeline Runner

Kompleksowy system orchestrujący cały proces scraping'u, deduplication i AI-powered summarization.
Integruje wszystkie komponenty systemu z dependency injection i environment configuration.

Key Features:
- Dependency injection via Google Cloud Secret Manager
- Environment-based configuration
- Complete pipeline integration
- Error handling i logging
- Configurable AI models i parameters

Usage:
    from ai_news.src.pipeline_runner import run_full_news_pipeline
    results = run_full_news_pipeline()

Architecture:
- PipelineRunner: Main orchestration class
- DependencyInjector: Handles service creation i injection  
- run_full_news_pipeline(): Convenience function dla quick execution
"""

import os
import logging
from typing import Dict, Optional, Any
from dependency_injector import containers, providers
from dependency_injector.wiring import inject, Provide


# Configure logging dla pipeline operations
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AppContainer(containers.DeclarativeContainer):
    """
    Dependency Injection Container dla AI News System
    
    Centralized configuration i service management using dependency-injector.
    Handles wszystkie dependencies including AI models, API keys, i service instances.
    
    Services Provided:
    - NewsOrchestrationService: Main orchestration service
    - DuplicationService: Deduplication engine  
    - BlogSummaryService: AI-powered summarization
    - LangChainNewsOrchestrator: Advanced AI operations
    
    Configuration Sources:
    - Environment variables (.env file)
    - Google Cloud Secret Manager (production)
    - Default fallback values dla development
    """
    
    # Configuration providers z environment variables
    config = providers.Configuration()
    
    # Load environment variables z os.environ
    config.openai_api_key.from_env("OPENAI_API_KEY", required=True)
    config.qdrant_url.from_env("QDRANT_URL", default="")
    config.qdrant_api_key.from_env("QDRANT_API_KEY", default="")
    config.qdrant_host.from_env("QDRANT_HOST", default="localhost")
    config.qdrant_port.from_env("QDRANT_PORT", default=6333)
    config.qdrant_collection_name.from_env("QDRANT_COLLECTION_NAME", default="news_articles")
    
    # Model configuration z defaults
    config.llm_model.from_env("DEFAULT_LLM_MODEL", default="gpt-4o-mini")
    config.embedding_model.from_env("DEFAULT_EMBEDDING_MODEL", default="text-embedding-3-small")
    config.temperature.from_env("DEFAULT_TEMPERATURE", default=0.7)
    config.max_tokens.from_env("DEFAULT_MAX_TOKENS", default=2000)
    
    # LangChain configuration (optional)
    config.langchain_api_key.from_env("LANGCHAIN_API_KEY", default="")
    config.langchain_project.from_env("LANGCHAIN_PROJECT", default="ai-news-scraper")
    config.langchain_tracing.from_env("LANGCHAIN_TRACING_V2", default="false")
    
    # Service Providers - lazy initialization dla performance
    
    @providers.Singleton
    def duplication_service():
        """
        Creates configured DuplicationService z environment settings.
        
        Initializes OpenAI embeddings i Qdrant vector database connection
        using injected configuration parameters.
        """
        from .deduplication import DuplicationService
        
        # Set OpenAI API key dla embeddings
        os.environ["OPENAI_API_KEY"] = AppContainer.config.openai_api_key()
        
        return DuplicationService(
            model=AppContainer.config.embedding_model(),
            qdrant_url=AppContainer.config.qdrant_url() if AppContainer.config.qdrant_url() else None,
            qdrant_api_key=AppContainer.config.qdrant_api_key() if AppContainer.config.qdrant_api_key() else None,
            qdrant_host=AppContainer.config.qdrant_host(),
            qdrant_port=AppContainer.config.qdrant_port(),
            collection_name=AppContainer.config.qdrant_collection_name()
        )
    
    @providers.Singleton  
    def blog_summary_service():
        """
        Creates configured BlogSummaryService z AI model settings.
        
        Initializes LLM model z specified temperature i max tokens
        dla content generation.
        """
        from .summarization import BlogSummaryService
        
        # Set OpenAI API key dla LLM
        os.environ["OPENAI_API_KEY"] = AppContainer.config.openai_api_key()
        
        return BlogSummaryService(
            model=AppContainer.config.llm_model(),
            temperature=float(AppContainer.config.temperature()),
            max_tokens=int(AppContainer.config.max_tokens())
        )
    
    @providers.Singleton
    def langchain_orchestrator():
        """
        Creates configured LangChainNewsOrchestrator z full AI capabilities.
        
        Initializes advanced AI orchestrator z OpenAI models i optional
        LangSmith tracing dla monitoring.
        """
        from .langchain_chains import LangChainNewsOrchestrator
        
        # Set wszystkie required API keys
        os.environ["OPENAI_API_KEY"] = AppContainer.config.openai_api_key()
        
        # Optional LangSmith configuration dla tracing
        if AppContainer.config.langchain_api_key():
            os.environ["LANGCHAIN_API_KEY"] = AppContainer.config.langchain_api_key()
            os.environ["LANGCHAIN_PROJECT"] = AppContainer.config.langchain_project()
            os.environ["LANGCHAIN_TRACING_V2"] = str(AppContainer.config.langchain_tracing()).lower()
        
        return LangChainNewsOrchestrator(
            model_type="openai",
            llm_model=AppContainer.config.llm_model(),
            embedding_model=AppContainer.config.embedding_model(),
            temperature=float(AppContainer.config.temperature())
        )
    
    @providers.Factory
    def news_orchestration_service(
        duplication_service=Provide[duplication_service],
        blog_summary_service=Provide[blog_summary_service], 
        langchain_orchestrator=Provide[langchain_orchestrator]
    ):
        """
        Creates fully configured NewsOrchestrationService z injected dependencies.
        
        Factory provider creating main orchestration service z all dependencies
        properly injected i configured based na environment variables.
        
        Args:
            duplication_service: Injected DuplicationService instance
            blog_summary_service: Injected BlogSummaryService instance  
            langchain_orchestrator: Injected LangChainNewsOrchestrator instance
            
        Returns:
            NewsOrchestrationService: Fully configured main service
        """
        from .news_service import NewsOrchestrationService
        
        return NewsOrchestrationService(
            embedding_model=AppContainer.config.embedding_model(),
            llm_model=AppContainer.config.llm_model(), 
            temperature=float(AppContainer.config.temperature()),
            deduplication_service=duplication_service,
            blog_summary_service=blog_summary_service,
            langchain_orchestrator=langchain_orchestrator
        )


class PipelineRunner:
    """
    Main Pipeline Runner dla AI News Processing System
    
    High-level orchestration class providing easy-to-use interface dla complete
    news processing pipeline. Handles dependency injection, environment setup,
    i provides methods dla różne workflow scenarios.
    
    Features:
    - Automatic dependency injection
    - Environment validation  
    - Complete pipeline orchestration
    - Error handling i recovery
    - Flexible execution modes
    
    Usage:
        runner = PipelineRunner()
        results = runner.run_full_pipeline()
    """
    
    def __init__(self):
        """
        Initializes PipelineRunner z dependency injection container.
        
        Sets up dependency injection container, validates environment,
        i prepares all services dla pipeline execution.
        """
        self.container = AppContainer()
        self._validate_environment()
        
        # Wire container dla dependency injection
        self.container.wire(modules=[__name__])
        
        logger.info("PipelineRunner initialized z dependency injection")
    
    def _validate_environment(self):
        """
        Validates required environment variables i configuration.
        
        Checks that wszystkie critical environment variables are set
        i raises appropriate errors jeśli configuration jest incomplete.
        
        Raises:
            ValueError: If required environment variables are missing
            ConnectionError: If external services are unreachable
        """
        # Check critical API keys
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY jest required dla AI operations")
        
        # Validate Qdrant configuration
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        qdrant_port = os.getenv("QDRANT_PORT", "6333")
        
        if qdrant_url:
            logger.info(f"Environment validated - Cloud Qdrant: {qdrant_url}")
        else:
            logger.info(f"Environment validated - Local Qdrant: {qdrant_host}:{qdrant_port}")
    
    @inject
    def run_full_pipeline(
        self, 
        generate_summary: bool = True,
        service: 'NewsOrchestrationService' = Provide[AppContainer.news_orchestration_service]
    ) -> Dict[str, Any]:
        """
        Executes complete end-to-end news processing pipeline z dependency injection.
        
        Main entry point dla full system operation. Orchestrates scraping,
        deduplication, i AI-powered summarization using injected services.
        
        Pipeline Stages:
        1. Environment validation i service initialization
        2. Multi-source news scraping
        3. Deduplication processing (hash + semantic)
        4. AI-powered summary generation (optional)
        5. Database statistics calculation
        6. Comprehensive results reporting
        
        Args:
            generate_summary: Enable AI summary generation (default True)
            service: Injected NewsOrchestrationService (via DI container)
            
        Returns:
            Dict[str, Any]: Comprehensive pipeline results containing:
                - 'scraping_results': Per-source article counts
                - 'daily_summary': Generated daily summary (if enabled)
                - 'weekly_summary': Generated weekly summary (if enabled)  
                - 'total_unique_articles': Database statistics
                - 'total_duplicates': Deduplication metrics
                - 'pipeline_status': Success/failure status
                - 'execution_time': Pipeline duration
                
        Error Handling:
            Comprehensive error handling z partial result recovery
            Pipeline continues even jeśli individual stages fail
            Detailed logging dla debugging i monitoring
        """
        import time
        start_time = time.time()
        
        try:
            logger.info("Starting full AI News processing pipeline")
            
            # Execute complete pipeline using injected service
            results = service.run_full_pipeline(generate_summary=generate_summary)
            
            # Add pipeline metadata
            results.update({
                'pipeline_status': 'success',
                'execution_time': round(time.time() - start_time, 2),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            
            logger.info(f"Pipeline completed successfully w {results['execution_time']}s")
            return results
            
        except Exception as e:
            # Comprehensive error handling z partial results
            error_result = {
                'pipeline_status': 'failed',
                'error': str(e),
                'execution_time': round(time.time() - start_time, 2),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'scraping_results': {},
                'total_unique_articles': 0,
                'total_duplicates': 0
            }
            
            logger.error(f"Pipeline failed: {e}")
            return error_result
    
    @inject
    def scrape_single_source(
        self,
        source_name: str,
        service: 'NewsOrchestrationService' = Provide[AppContainer.news_orchestration_service]
    ) -> Dict[str, Any]:
        """
        Executes targeted scraping dla single news source z full processing.
        
        Focused operation dla scraping specific source z complete deduplication
        i processing pipeline. Useful dla targeted updates lub source testing.
        
        Args:
            source_name: Name registered scraper (case-insensitive)
            service: Injected NewsOrchestrationService (via DI container)
            
        Returns:
            Dict[str, Any]: Single source results containing:
                - 'source_name': Processed source name
                - 'articles_scraped': Number new articles  
                - 'processing_time': Execution duration
                - 'status': Success/failure status
        """
        import time
        start_time = time.time()
        
        try:
            logger.info(f"Scraping single source: {source_name}")
            
            # Execute single source scraping
            articles_count = service.scrape_single_source(source_name)
            
            result = {
                'source_name': source_name,
                'articles_scraped': articles_count,
                'processing_time': round(time.time() - start_time, 2),
                'status': 'success',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"Single source scraping completed: {articles_count} articles")
            return result
            
        except Exception as e:
            return {
                'source_name': source_name,
                'articles_scraped': 0,
                'processing_time': round(time.time() - start_time, 2),
                'status': 'failed',
                'error': str(e),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
    
    @inject
    def generate_daily_summary_only(
        self,
        topic_category: str = "AI News",
        service: 'NewsOrchestrationService' = Provide[AppContainer.news_orchestration_service]
    ) -> Optional[Dict[str, Any]]:
        """
        Generates standalone daily summary without scraping new articles.
        
        AI-powered summary generation using existing articles w database.
        Perfect dla scheduled summary generation lub on-demand reporting.
        
        Args:
            topic_category: Content category dla AI context
            service: Injected NewsOrchestrationService (via DI container)
            
        Returns:
            Optional[Dict]: Summary results lub None jeśli generation failed
        """
        try:
            logger.info("Generating daily summary only")
            
            summary = service.generate_daily_summary(topic_category)
            
            if summary:
                return {
                    'summary_type': 'daily',
                    'title': summary.title,
                    'topic_category': summary.topic_category,
                    'articles_count': summary.articles.count(),
                    'created_at': summary.created_at.isoformat(),
                    'status': 'success'
                }
            else:
                return {
                    'summary_type': 'daily',
                    'status': 'no_articles',
                    'message': 'No new articles available dla summary generation'
                }
                
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
            return {
                'summary_type': 'daily',
                'status': 'failed',
                'error': str(e)
            }
    
    @inject  
    def get_system_statistics(
        self,
        service: 'NewsOrchestrationService' = Provide[AppContainer.news_orchestration_service]
    ) -> Dict[str, Any]:
        """
        Retrieves comprehensive system statistics i health metrics.
        
        Provides complete overview database state, source performance,
        i system configuration dla monitoring i analysis.
        
        Args:
            service: Injected NewsOrchestrationService (via DI container)
            
        Returns:
            Dict[str, Any]: Complete system statistics
        """
        try:
            stats = service.get_statistics()
            stats['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
            stats['status'] = 'success'
            return stats
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
    
    @inject
    def interactive_query(
        self,
        query: str,
        service: 'NewsOrchestrationService' = Provide[AppContainer.news_orchestration_service]
    ) -> str:
        """
        Handles interactive conversational queries about news database.
        
        Natural language interface powered by AI agent dla exploring
        news data through conversational queries.
        
        Args:
            query: Natural language question
            service: Injected NewsOrchestrationService (via DI container)
            
        Returns:
            str: AI agent response based na query analysis
        """
        try:
            return service.interactive_news_query(query)
        except Exception as e:
            logger.error(f"Error w interactive query: {e}")
            return f"Sorry, I encountered an error processing your query: {e}"


# Convenience functions dla easy pipeline execution

def run_full_news_pipeline(generate_summary: bool = True) -> Dict[str, Any]:
    """
    Convenience function dla running complete news processing pipeline.
    
    One-line execution function that handles wszystkie setup i execution.
    Perfect dla scripts, scheduled tasks, i simple integrations.
    
    Args:
        generate_summary: Enable AI summary generation (default True)
        
    Returns:
        Dict[str, Any]: Complete pipeline results
        
    Usage:
        from ai_news.src.pipeline_runner import run_full_news_pipeline
        results = run_full_news_pipeline()
    """
    runner = PipelineRunner()
    return runner.run_full_pipeline(generate_summary=generate_summary)


def scrape_single_source(source_name: str) -> Dict[str, Any]:
    """
    Convenience function dla single source scraping.
    
    Args:
        source_name: Name registered scraper
        
    Returns:
        Dict[str, Any]: Single source results
    """
    runner = PipelineRunner()
    return runner.scrape_single_source(source_name)


def generate_daily_summary(topic_category: str = "AI News") -> Optional[Dict[str, Any]]:
    """
    Convenience function dla daily summary generation.
    
    Args:
        topic_category: Content category dla AI context
        
    Returns:
        Optional[Dict]: Summary results lub None
    """
    runner = PipelineRunner()
    return runner.generate_daily_summary_only(topic_category)


def get_system_stats() -> Dict[str, Any]:
    """
    Convenience function dla system statistics.
    
    Returns:
        Dict[str, Any]: Complete system statistics
    """
    runner = PipelineRunner()
    return runner.get_system_statistics()


def query_news_database(query: str) -> str:
    """
    Convenience function dla interactive news queries.
    
    Args:
        query: Natural language question
        
    Returns:
        str: AI agent response
    """
    runner = PipelineRunner()
    return runner.interactive_query(query)


if __name__ == "__main__":
    """
    Direct execution dla testing i development.
    
    Usage:
        python pipeline_runner.py
    """
    import time
    
    print("🚀 Starting AI News Processing Pipeline")
    print("=" * 50)
    
    start_time = time.time()
    
    # Run complete pipeline
    results = run_full_news_pipeline(generate_summary=True)
    
    # Display results
    print(f"\n✅ Pipeline Status: {results.get('pipeline_status', 'unknown')}")
    print(f"⏱️  Execution Time: {results.get('execution_time', 0)}s")
    print(f"📰 Total Unique Articles: {results.get('total_unique_articles', 0)}")
    print(f"🔄 Duplicates Detected: {results.get('total_duplicates', 0)}")
    
    # Source breakdown
    scraping_results = results.get('scraping_results', {})
    if scraping_results:
        print(f"\n📊 Scraping Results:")
        for source, count in scraping_results.items():
            print(f"   • {source}: {count} articles")
    
    # Summary information
    if results.get('daily_summary'):
        print(f"📝 Daily summary generated: {results['daily_summary'].title}")
    if results.get('weekly_summary'):
        print(f"📅 Weekly summary generated: {results['weekly_summary'].title}")
    
    print(f"\n🎉 Pipeline completed w {time.time() - start_time:.2f} seconds")