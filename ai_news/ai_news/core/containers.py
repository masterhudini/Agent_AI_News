"""
Dependency injection container configuration for AI News application.
Uses dependency-injector framework for clean, testable dependency management.
"""
from dependency_injector import containers, providers

from .config import get_app_config


class ApplicationContainer(containers.DeclarativeContainer):
    """Main application dependency injection container."""
    
    # Configuration
    config = providers.Factory(get_app_config)
    
    # Basic clients and services
    qdrant_client = providers.Factory(
        "qdrant_client.QdrantClient",
        host=config.provided.qdrant_host,
        port=config.provided.qdrant_port,
        api_key=config.provided.qdrant_api_key
    )
    
    openai_embeddings = providers.Factory(
        "langchain_openai.OpenAIEmbeddings",
        model=config.provided.default_embedding_model,
        api_key=config.provided.openai_api_key
    )
    
    chat_openai = providers.Factory(
        "langchain_openai.ChatOpenAI",
        model=config.provided.default_llm_model,
        temperature=config.provided.default_temperature,
        api_key=config.provided.openai_api_key
    )
    
    # Core services
    vector_deduplicator = providers.Singleton(
        "ai_news.src.deduplication.VectorDeduplicator",
        qdrant_host=config.provided.qdrant_host,
        qdrant_port=config.provided.qdrant_port,
        collection_name=config.provided.qdrant_collection_name,
        model=config.provided.default_embedding_model
    )
    
    content_hash_deduplicator = providers.Factory(
        "ai_news.src.deduplication.ContentHashDeduplicator"
    )
    
    deduplication_service = providers.Singleton(
        "ai_news.src.deduplication.DuplicationService",
        model=config.provided.default_embedding_model
    )
    
    # LangChain services
    news_analyzer = providers.Factory(
        "ai_news.src.langchain_chains.NewsAnalyzer",
        model=config.provided.default_llm_model,
        temperature=0.3  # Lower temperature for factual analysis
    )
    
    blog_generator = providers.Factory(
        "ai_news.src.langchain_chains.BlogGenerator", 
        model=config.provided.default_llm_model,
        temperature=config.provided.default_temperature
    )
    
    news_processing_agent = providers.Factory(
        "ai_news.src.langchain_chains.NewsProcessingAgent",
        model=config.provided.default_llm_model
    )
    
    langchain_orchestrator = providers.Singleton(
        "ai_news.src.langchain_chains.LangChainNewsOrchestrator",
        model_type="openai",
        model=config.provided.default_llm_model
    )
    
    # Summarization services
    blog_summarizer = providers.Factory(
        "ai_news.src.summarization.BlogSummarizer",
        model=config.provided.default_llm_model,
        temperature=config.provided.default_temperature
    )
    
    blog_summary_service = providers.Singleton(
        "ai_news.src.summarization.BlogSummaryService",
        model=config.provided.default_llm_model,
        temperature=config.provided.default_temperature
    )
    
    # Main orchestration service
    news_orchestration_service = providers.Singleton(
        "ai_news.src.news_service.NewsOrchestrationService",
        embedding_model=config.provided.default_embedding_model,
        llm_model=config.provided.default_llm_model,
        temperature=config.provided.default_temperature,
        deduplication_service=deduplication_service,
        blog_summary_service=blog_summary_service,
        langchain_orchestrator=langchain_orchestrator
    )


# Global container instance
container = ApplicationContainer()