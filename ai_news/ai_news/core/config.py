"""
Configuration management for AI News application with environment-specific settings.
Supports both development (environment variables) and production (GCP Secret Manager) modes.
"""
import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Application configuration data class."""
    
    # API Keys
    openai_api_key: Optional[str] = None
    qdrant_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None
    langchain_api_key: Optional[str] = None
    
    # Model configurations
    default_llm_model: str = "gpt-4o-mini"
    default_embedding_model: str = "text-embedding-3-small"
    default_temperature: float = 0.7
    default_max_tokens: int = 2000
    
    # Qdrant configuration
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "news_articles"
    
    # LangChain configuration
    langchain_tracing_v2: bool = True
    langchain_project: str = "ai-news-scraper"
    
    # Environment
    environment: str = "development"


class ConfigProvider(ABC):
    """Abstract base class for configuration providers."""
    
    @abstractmethod
    def get_config(self) -> AppConfig:
        """Get application configuration."""
        pass
    
    @abstractmethod
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get a specific secret value."""
        pass


class EnvironmentConfigProvider(ConfigProvider):
    """Configuration provider that reads from environment variables."""
    
    def get_config(self) -> AppConfig:
        """Load configuration from environment variables."""
        return AppConfig(
            # API Keys from environment
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            qdrant_url=os.getenv('QDRANT_URL'),
            qdrant_api_key=os.getenv('QDRANT_API_KEY'),
            langchain_api_key=os.getenv('LANGCHAIN_API_KEY'),
            
            # Model configurations with defaults
            default_llm_model=os.getenv('DEFAULT_LLM_MODEL', 'gpt-4o-mini'),
            default_embedding_model=os.getenv('DEFAULT_EMBEDDING_MODEL', 'text-embedding-3-small'),
            default_temperature=float(os.getenv('DEFAULT_TEMPERATURE', '0.7')),
            default_max_tokens=int(os.getenv('DEFAULT_MAX_TOKENS', '2000')),
            
            # Qdrant configuration
            qdrant_host=os.getenv('QDRANT_HOST', 'localhost'),
            qdrant_port=int(os.getenv('QDRANT_PORT', '6333')),
            qdrant_collection_name=os.getenv('QDRANT_COLLECTION_NAME', 'news_articles'),
            
            # LangChain configuration
            langchain_tracing_v2=os.getenv('LANGCHAIN_TRACING_V2', 'true').lower() == 'true',
            langchain_project=os.getenv('LANGCHAIN_PROJECT', 'ai-news-scraper'),
            
            # Environment
            environment=os.getenv('ENVIRONMENT', 'development')
        )
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from environment variable."""
        return os.getenv(secret_name)


class GCPSecretManagerProvider(ConfigProvider):
    """Configuration provider that reads from GCP Secret Manager."""
    
    def __init__(self, project_id: str):
        """
        Initialize GCP Secret Manager provider.
        
        Args:
            project_id: GCP project ID containing the secrets
        """
        self.project_id = project_id
        self._client = None
        self._config_cache: Optional[AppConfig] = None
    
    @property
    def client(self):
        """Lazy initialization of Secret Manager client."""
        if self._client is None:
            try:
                from google.cloud import secretmanager
                self._client = secretmanager.SecretManagerServiceClient()
            except ImportError:
                logger.error("google-cloud-secret-manager not installed")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize Secret Manager client: {e}")
                raise
        return self._client
    
    def get_secret(self, secret_name: str, version: str = "latest") -> Optional[str]:
        """
        Get secret value from GCP Secret Manager.
        
        Args:
            secret_name: Name of the secret
            version: Secret version (default: "latest")
            
        Returns:
            Secret value or None if not found
        """
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"
            response = self.client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.warning(f"Failed to get secret '{secret_name}': {e}")
            return None
    
    def get_config(self) -> AppConfig:
        """Load configuration from GCP Secret Manager with fallback to environment."""
        if self._config_cache is not None:
            return self._config_cache
        
        try:
            # Load secrets from GCP Secret Manager
            config = AppConfig(
                # API Keys from Secret Manager
                openai_api_key=self.get_secret('openai-api-key'),
                qdrant_url=self.get_secret('qdrant-url'),
                qdrant_api_key=self.get_secret('qdrant-api-key'), 
                langchain_api_key=self.get_secret('langchain-api-key'),
                
                # Model configurations (fallback to environment, then defaults)
                default_llm_model=self.get_secret('default-llm-model') or os.getenv('DEFAULT_LLM_MODEL', 'gpt-4o-mini'),
                default_embedding_model=self.get_secret('default-embedding-model') or os.getenv('DEFAULT_EMBEDDING_MODEL', 'text-embedding-3-small'),
                default_temperature=float(self.get_secret('default-temperature') or os.getenv('DEFAULT_TEMPERATURE', '0.7')),
                default_max_tokens=int(self.get_secret('default-max-tokens') or os.getenv('DEFAULT_MAX_TOKENS', '2000')),
                
                # Qdrant configuration (fallback to environment)
                qdrant_host=self.get_secret('qdrant-host') or os.getenv('QDRANT_HOST', 'localhost'),
                qdrant_port=int(self.get_secret('qdrant-port') or os.getenv('QDRANT_PORT', '6333')),
                qdrant_collection_name=self.get_secret('qdrant-collection-name') or os.getenv('QDRANT_COLLECTION_NAME', 'news_articles'),
                
                # LangChain configuration (fallback to environment)
                langchain_tracing_v2=(self.get_secret('langchain-tracing-v2') or os.getenv('LANGCHAIN_TRACING_V2', 'true')).lower() == 'true',
                langchain_project=self.get_secret('langchain-project') or os.getenv('LANGCHAIN_PROJECT', 'ai-news-scraper'),
                
                # Environment
                environment='production'
            )
            
            # Cache the configuration
            self._config_cache = config
            return config
            
        except Exception as e:
            logger.error(f"Failed to load configuration from GCP Secret Manager: {e}")
            logger.info("Falling back to environment variables")
            # Fallback to environment variables
            env_provider = EnvironmentConfigProvider()
            return env_provider.get_config()


def get_config_provider() -> ConfigProvider:
    """
    Factory function to get appropriate configuration provider based on environment.
    
    Returns:
        ConfigProvider: Environment or GCP Secret Manager provider
    """
    environment = os.getenv('ENVIRONMENT', 'development').lower()
    
    if environment == 'production':
        gcp_project_id = os.getenv('GCP_PROJECT_ID')
        if gcp_project_id:
            logger.info("Using GCP Secret Manager configuration provider")
            return GCPSecretManagerProvider(gcp_project_id)
        else:
            logger.warning("GCP_PROJECT_ID not set, falling back to environment variables")
            return EnvironmentConfigProvider()
    else:
        logger.info("Using environment variable configuration provider")
        return EnvironmentConfigProvider()


# Global configuration instance
_config_provider: Optional[ConfigProvider] = None
_app_config: Optional[AppConfig] = None


def get_app_config() -> AppConfig:
    """
    Get application configuration singleton.
    
    Returns:
        AppConfig: Application configuration instance
    """
    global _config_provider, _app_config
    
    if _app_config is None:
        if _config_provider is None:
            _config_provider = get_config_provider()
        _app_config = _config_provider.get_config()
    
    return _app_config


def reset_config():
    """Reset configuration cache - useful for testing."""
    global _config_provider, _app_config
    _config_provider = None
    _app_config = None