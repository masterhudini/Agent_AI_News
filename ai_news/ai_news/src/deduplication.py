from typing import List, Dict, Optional, Tuple
import logging
from django.conf import settings

# LangChain imports - zintegrowane z OpenAI i Qdrant dla Python 3.12
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Logger dla systemu deduplikacji
logger = logging.getLogger(__name__)


class VectorDeduplicator:
    """
    Semantic deduplication engine wykorzystujący OpenAI embeddings i Qdrant vector DB.
    
    Jest to zaawansowany system wykrywania semantycznie podobnych artykułów, który idzie
    daleko poza proste porównywanie tekstów. Używa AI embeddings do zrozumienia
    znaczenia treści i wykrywania duplikatów nawet gdy są przepisane lub sparafrazowane.
    
    Architektura:
    - OpenAI text-embedding-3-small: Konwersja tekstu na 1536-wymiarowe wektory
    - Qdrant Vector Database: Hochwydajne przechowywanie i search wektorów
    - LangChain integration: Unified interface do vector operations
    - Threshold-based similarity: Konfigurowalny próg podobieństwa (default 85%)
    
    Wykorzystywana przez:
    - DuplicationService jako drugi poziom deduplikacji (po exact hash)
    - NewsOrchestrationService do search_similar_articles()
    - LangChain agents do semantic search w bazie artykułów
    
    Performance considerations:
    - Embeddings: ~$0.00013 per 1K tokens (OpenAI pricing)
    - Vector search: Sub-second response dla milionów artykułów
    - Memory usage: ~6MB na 1000 artykułów w index
    
    Note:
        Wymaga działającego Qdrant serwera i OpenAI API key.
        Automatically tworzy kolekcję przy pierwszym użyciu.
    """
    
    def __init__(self, 
                 qdrant_url: str = None,
                 qdrant_api_key: str = None,
                 qdrant_host: str = "localhost",
                 qdrant_port: int = 6333,
                 collection_name: str = "news_articles",
                 similarity_threshold: float = 0.85,
                 model: str = "text-embedding-3-small",
                 qdrant_client=None,
                 embeddings=None):
        """
        Inicjalizuje VectorDeduplicator z konfiguracją Qdrant i OpenAI.
        
        Ustala połączenie z Qdrant vector database, konfiguruje OpenAI embeddings
        i przygotowuje text splitter do przetwarzania długich dokumentów.
        Supports dependency injection for better testability.
        
        Args:
            qdrant_url: Cloud Qdrant URL (np. https://xyz.gcp.cloud.qdrant.io)
            qdrant_api_key: API key dla cloud Qdrant (wymagane dla cloud)
            qdrant_host: Adres serwera Qdrant dla local (default localhost)
            qdrant_port: Port serwera Qdrant dla local (default 6333)
            collection_name: Nazwa kolekcji w Qdrant (default "news_articles")
            similarity_threshold: Próg podobieństwa 0.0-1.0 (default 0.85 = 85%)
            model: Model OpenAI embeddings (default "text-embedding-3-small")
            qdrant_client: Injected Qdrant client (optional)
            embeddings: Injected OpenAI embeddings (optional)
            
        Note:
            Automatically tworzy kolekcję Qdrant jeśli nie istnieje.
            Uses injected dependencies or creates new instances.
        """
        # Use injected client or create new one
        if qdrant_client is not None:
            self.client = qdrant_client
        else:
            # Prioritize cloud URL over local host/port
            if qdrant_url:
                # Cloud Qdrant connection
                self.client = QdrantClient(
                    url=qdrant_url,
                    api_key=qdrant_api_key
                )
                logger.info(f"Connected to cloud Qdrant: {qdrant_url}")
            else:
                # Local Qdrant connection
                self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
                logger.info(f"Connected to local Qdrant: {qdrant_host}:{qdrant_port}")
            
        self.collection_name = collection_name
        self.similarity_threshold = similarity_threshold
        
        # Use injected embeddings or create new ones
        if embeddings is not None:
            self.embeddings = embeddings
        else:
            from ..core.config import get_app_config
            config = get_app_config()
            self.embeddings = OpenAIEmbeddings(
                model=model,
                api_key=config.openai_api_key
            )
        self.embedding_size = 1536  # Rozmiar wektorów dla text-embedding-3-small
        
        # Text splitter dla długich dokumentów - intelligent chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,     # Maksymalny rozmiar chunka
            chunk_overlap=100,   # Overlap między chunkami dla kontekstu
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]  # Hierarchical splitting
        )
        
        # Zapewniamy że kolekcja Qdrant istnieje
        self._ensure_collection_exists()
        
        # Inicjalizujemy LangChain Qdrant vector store dla unified interface
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embeddings=self.embeddings
        )
    
    def _ensure_collection_exists(self):
        """
        Zapewnia że kolekcja Qdrant istnieje, tworzy ją jeśli potrzeba.
        
        Sprawdza czy kolekcja o zadanej nazwie już istnieje w Qdrant.
        Jeśli nie, tworzy nową kolekcję z odpowiednimi parametrami wektorów.
        
        Konfiguracja kolekcji:
        - Vector size: 1536 (text-embedding-3-small)
        - Distance metric: Cosine similarity
        - Optimized for semantic search
        
        Wywoływana przez:
        - __init__() podczas inicjalizacji
        
        Raises:
            Exception: Przy problemach z połączeniem do Qdrant
        """
        try:
            # Pobieramy listę istniejących kolekcji
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            # Sprawdzamy czy nasza kolekcja już istnieje
            if self.collection_name not in collection_names:
                # Tworzymy nową kolekcję z cosine similarity dla semantic search
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_size,  # 1536 dla text-embedding-3-small
                        distance=Distance.COSINE    # Najlepsze dla semantic similarity
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error creating Qdrant collection: {e}")
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generuje embedding vector dla podanego tekstu używając OpenAI API.
        
        Konwertuje tekst na 1536-wymiarowy wektor numeryczny reprezentujący
        semantic meaning treści. Używa modelu text-embedding-3-small.
        
        Args:
            text: Tekst do przekonwertowania na embedding
            
        Returns:
            List[float]: 1536-wymiarowy wektor reprezentujący semantic meaning
            
        Note:
            Może kosztować ~$0.00013 per 1K tokenów (OpenAI pricing)
        """
        return self.embeddings.embed_query(text)
    
    def _create_searchable_text(self, article) -> str:
        """
        Tworzy tekst do indeksowania łączący tytuł i treść artykułu.
        
        Kombinuje najważniejsze pola artykułu w jeden tekst do semantic search.
        Tytuł jest szczególnie ważny dla określenia tematu artykułu.
        
        Args:
            article: NewsArticle object z title i content
            
        Returns:
            str: Połączony tekst "title content" do embeddingu
        """
        return f"{article.title} {article.content}"
    
    def _create_document(self, article) -> Document:
        """
        Tworzy LangChain Document z artykułu dla vector store.
        
        Konwertuje NewsArticle na format Document używany przez LangChain
        z pełnym tekstem i metadata. Metadata jest używana do filtrowania
        i identyfikacji wyników podczas search.
        
        Args:
            article: NewsArticle object do konwersji
            
        Returns:
            Document: LangChain Document z page_content i metadata
        """
        # Przygotowujemy searchable text z title + content
        content = self._create_searchable_text(article)
        
        # Tworzymy Document z comprehensive metadata
        return Document(
            page_content=content,
            metadata={
                "article_id": article.id,           # ID dla referencji
                "title": article.title,             # Tytuł dla display
                "source": article.source,           # Źródło dla grupowania
                "url": article.url,                 # URL dla weryfikacji
                "published_date": str(article.published_date),  # Data dla sortowania
                "content_hash": article.content_hash  # Hash dla exact deduplication
            }
        )
    
    def find_similar_articles(self, article, limit: int = 5) -> List[Tuple]:
        """
        Znajduje semantycznie podobne artykuły używając LangChain vector search.
        
        Główna metoda do wykrywania duplikatów semantycznych. Konwertuje artykuł
        na embedding i przeszukuje vector store w poszukiwaniu podobnych treści.
        
        Wykorzystywana przez:
        - DuplicationService.process_article_for_duplicates() - wykrywanie duplikatów
        - NewsOrchestrationService.search_similar_articles() - user queries
        - LangChain agents - semantic search w bazie artykułów
        
        Args:
            article: NewsArticle object do porównania
            limit: Maksymalna liczba podobnych artykułów do zwrócenia (default 5)
            
        Returns:
            List[Tuple]: Lista tupli (Document, similarity_score) dla podobnych artykułów
                        Posortowana według similarity score (malejąco)
                        
        Note:
            Używa similarity_threshold (default 0.85) do filtrowania wyników.
            Score 1.0 = identyczne, 0.0 = kompletnie różne.
        """
        from ..models import NewsArticle
        
        try:
            query_text = self._create_searchable_text(article)
            
            # Używamy LangChain similarity search z relevance scores
            # score_threshold filtruje wyniki poniżej naszego progu (default 85%)
            similar_docs = self.vector_store.similarity_search_with_relevance_scores(
                query=query_text,
                k=limit,
                score_threshold=self.similarity_threshold
            )
            
            # Konwertujemy Documents z powrotem na NewsArticle objects
            similar_articles = []
            for doc, relevance_score in similar_docs:
                try:
                    article_id = doc.metadata.get("article_id")
                    # Pomijamy ten sam artykuł i invalid IDs
                    if article_id and article_id != article.id:
                        similar_article = NewsArticle.objects.get(id=article_id)
                        similar_articles.append((similar_article, relevance_score))
                except (NewsArticle.DoesNotExist, ValueError):
                    # Graceful handling missing articles (mogły być usunięte)
                    continue
            
            return similar_articles
            
        except Exception as e:
            logger.error(f"Error searching for similar articles: {e}")
            return []
    
    def add_article_to_index(self, article) -> bool:
        """Add article to vector index using LangChain"""
        try:
            document = self._create_document(article)
            
            # Add to vector store with unique ID
            ids = [str(article.id)]
            self.vector_store.add_documents(documents=[document], ids=ids)
            
            # Store embedding for later use (optional)
            try:
                embedding = self.embeddings.embed_query(document.page_content)
                article.embedding_vector = embedding
                article.save(update_fields=['embedding_vector'])
            except Exception as embed_error:
                logger.warning(f"Could not store embedding: {embed_error}")
            
            logger.info(f"Added article to vector index: {article.title}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding article to index: {e}")
            return False
    
    def check_and_mark_duplicates(self, article) -> bool:
        """Check for duplicates and mark them"""
        similar_articles = self.find_similar_articles(article)
        
        if similar_articles:
            original_article, similarity_score = similar_articles[0]
            article.is_duplicate = True
            article.duplicate_of = original_article
            article.save(update_fields=['is_duplicate', 'duplicate_of'])
            
            logger.info(f"Marked article as duplicate: {article.title} "
                       f"(similar to: {original_article.title}, score: {similarity_score:.3f})")
            return True
        
        return False
    
    def remove_article_from_index(self, article_id: int):
        """Remove article from vector index"""
        try:
            # Use Qdrant client directly for deletion by ID
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[article_id]
            )
            logger.info(f"Removed article {article_id} from vector index")
        except Exception as e:
            logger.error(f"Error removing article from index: {e}")
    
    def search_similar_content(self, query: str, limit: int = 5) -> List:
        """Search for content similar to query"""
        from ..models import NewsArticle
        
        try:
            similar_docs = self.vector_store.similarity_search(
                query=query,
                k=limit
            )
            
            similar_articles = []
            for doc in similar_docs:
                try:
                    article_id = doc.metadata.get("article_id")
                    if article_id:
                        article = NewsArticle.objects.get(id=article_id)
                        similar_articles.append(article)
                except (NewsArticle.DoesNotExist, ValueError):
                    continue
            
            return similar_articles
            
        except Exception as e:
            logger.error(f"Error searching similar content: {e}")
            return []
    
    def get_collection_info(self) -> Dict:
        """Get collection information"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "status": info.status,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "embedding_model": self.embeddings.model,
                "embedding_size": self.embedding_size
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {}


class ContentHashDeduplicator:
    """Simple content hash-based deduplication"""
    
    @staticmethod
    def find_hash_duplicates(article) -> Optional:
        from ..models import NewsArticle
        
        try:
            existing_article = NewsArticle.objects.filter(
                content_hash=article.content_hash
            ).exclude(id=article.id).first()
            
            return existing_article
        except Exception as e:
            logger.error(f"Error finding hash duplicates: {e}")
            return None
    
    @staticmethod
    def mark_as_hash_duplicate(article, original):
        article.is_duplicate = True
        article.duplicate_of = original
        article.save(update_fields=['is_duplicate', 'duplicate_of'])
        
        logger.info(f"Marked article as hash duplicate: {article.title} "
                   f"(duplicate of: {original.title})")


class DuplicationService:
    """Streamlined duplication service using only LangChain and OpenAI"""
    
    def __init__(self, model: str = "text-embedding-3-small", 
                 qdrant_url: str = None, 
                 qdrant_api_key: str = None,
                 qdrant_host: str = "localhost",
                 qdrant_port: int = 6333,
                 collection_name: str = "news_articles",
                 vector_deduplicator=None, 
                 hash_deduplicator=None):
        if vector_deduplicator is not None:
            self.vector_deduplicator = vector_deduplicator
        else:
            self.vector_deduplicator = VectorDeduplicator(
                model=model,
                qdrant_url=qdrant_url,
                qdrant_api_key=qdrant_api_key,
                qdrant_host=qdrant_host,
                qdrant_port=qdrant_port,
                collection_name=collection_name
            )
            
        if hash_deduplicator is not None:
            self.hash_deduplicator = hash_deduplicator
        else:
            self.hash_deduplicator = ContentHashDeduplicator()
    
    def process_article_for_duplicates(self, article) -> bool:
        """Process article for both hash and semantic duplicates"""
        
        # First check for exact hash duplicates (faster)
        hash_duplicate = self.hash_deduplicator.find_hash_duplicates(article)
        if hash_duplicate:
            self.hash_deduplicator.mark_as_hash_duplicate(article, hash_duplicate)
            return True
        
        # Then check for semantic duplicates using LangChain + OpenAI
        if self.vector_deduplicator.check_and_mark_duplicates(article):
            return True
        
        # If no duplicates found, add to vector index for future comparisons
        self.vector_deduplicator.add_article_to_index(article)
        return False
    
    def get_unique_articles(self, limit: Optional[int] = None) -> List:
        """Get unique (non-duplicate) articles"""
        from ..models import NewsArticle
        
        queryset = NewsArticle.objects.filter(is_duplicate=False)
        if limit:
            queryset = queryset[:limit]
        return list(queryset)
    
    def search_similar_content(self, query: str, limit: int = 5) -> List:
        """Search for articles similar to a query"""
        return self.vector_deduplicator.search_similar_content(query, limit)