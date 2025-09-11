"""
Test dependency injection container configuration.
Provides isolated testing environment with mocked dependencies.
"""
from dependency_injector import containers, providers
from unittest.mock import Mock

from .config import AppConfig


class TestApplicationContainer(containers.DeclarativeContainer):
    """Test container with mocked dependencies for isolated testing."""
    
    # Test configuration with safe defaults
    config = providers.Factory(
        AppConfig,
        openai_api_key="test-openai-key",
        qdrant_url="http://test-qdrant:6333",
        qdrant_api_key="test-qdrant-key",
        langchain_api_key="test-langchain-key",
        default_llm_model="gpt-4o-mini",
        default_embedding_model="text-embedding-3-small",
        default_temperature=0.7,
        default_max_tokens=2000,
        qdrant_host="localhost",
        qdrant_port=6333,
        qdrant_collection_name="test_news_articles",
        langchain_tracing_v2=False,
        langchain_project="test-ai-news-scraper",
        environment="test"
    )
    
    # Mocked external services
    qdrant_client = providers.Factory(Mock)
    openai_embeddings = providers.Factory(Mock)
    chat_openai = providers.Factory(Mock)
    
    # Mocked core services
    vector_deduplicator = providers.Factory(Mock)
    content_hash_deduplicator = providers.Factory(Mock)
    deduplication_service = providers.Factory(Mock)
    
    # Mocked LangChain services
    news_analyzer = providers.Factory(Mock)
    blog_generator = providers.Factory(Mock)
    news_processing_agent = providers.Factory(Mock)
    langchain_orchestrator = providers.Factory(Mock)
    
    # Mocked summarization services
    blog_summarizer = providers.Factory(Mock)
    blog_summary_service = providers.Factory(Mock)
    
    # Main orchestration service with mocked dependencies
    news_orchestration_service = providers.Factory(
        "ai_news.src.news_service.NewsOrchestrationService",
        embedding_model=config.provided.default_embedding_model,
        llm_model=config.provided.default_llm_model,
        temperature=config.provided.default_temperature,
        deduplication_service=deduplication_service,
        blog_summary_service=blog_summary_service,
        langchain_orchestrator=langchain_orchestrator
    )


# Global test container instance
test_container = TestApplicationContainer()