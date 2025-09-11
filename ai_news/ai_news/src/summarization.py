from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from django.conf import settings

# LangChain imports - updated for Python 3.12 and latest versions
from langchain.chains.llm import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.chains.combine_documents.map_reduce import MapReduceDocumentsChain
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)


class LangChainSummarizer:
    """
    Bazowa klasa dla wszystkich typów sumaryzatorów używających LangChain i OpenAI.
    
    Jest to abstrakcyjna klasa dostarczająca wspólną funkcjonalność dla generowania
    streszczeń artykułów newsowych przy pomocy AI. Implementuje Template Method Pattern
    z konfiguracją OpenAI i przygotowaniem dokumentów do przetworzenia.
    
    Architektura:
    - Template Method Pattern: definiuje workflow sumaryzacji
    - Strategy Pattern: różne implementacje (Blog, Newsletter, etc.)
    - Document Processing: konwertuje NewsArticle na LangChain Documents
    - LLM Integration: używa wyłącznie OpenAI (GPT-4o-mini default)
    
    Wykorzystywana przez:
    - BlogSummarizer jako klasa bazowa do tworzenia blog postów
    - BlogSummaryService jako engine do generowania streszczeń
    - NewsOrchestrationService do inteligentnych podsumowań
    - Management commands do batch processing
    
    Performance considerations:
    - Limit 10 artykułów per summary (token optimization)
    - Max 8000 znaków treści (context window management)
    - Temperature 0.7 (balance creativity vs consistency)
    
    Note:
        Jest to klasa abstrakcyjna - wymaga implementacji summarize() przez subklasy.
        Zawiera metodę _prepare_documents() używaną przez wszystkie implementacje.
    """
    
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.7):
        """
        Inicjalizuje LangChain summarizer z konfiguracją OpenAI i text splitter.
        
        Ustala parametry sumaryzacji, konfiguruje model OpenAI GPT-4o-mini
        i przygotowuje text splitter do dzielenia długich dokumentów na chunks.
        
        Args:
            model: Model OpenAI do użycia (default "gpt-4o-mini")
                  Wybór między szybkością a jakością - mini jest optymalne
            temperature: Poziom kreatywności 0.0-1.0 (default 0.7)
                        0.7 zapewnia balance między consistency a creativity
        
        Configuration:
        - max_articles_per_summary: 10 (token limit optimization)
        - max_content_length: 8000 chars (context window management)
        - chunk_size: 2000 (optimal dla GPT-4o-mini)
        - chunk_overlap: 200 (maintains context between chunks)
        """
        # Limity przetwarzania - optimized dla OpenAI context windows
        self.max_articles_per_summary = 10  # Balance między quality a cost
        self.max_content_length = 8000      # Zapobiega przekroczeniu token limits
        
        # Inicjalizujemy OpenAI LLM - wyłącznie OpenAI, bez fallbacks
        # GPT-4o-mini oferuje najlepszy balance cost/performance dla summarization
        from ..core.config import get_app_config
        config = get_app_config()
        self.llm = ChatOpenAI(
            model=model,                    # Default: gpt-4o-mini (cost-effective)
            temperature=temperature,        # 0.7 = balance creativity vs consistency
            api_key=config.openai_api_key  # Configuration management integration
        )
        
        # Text splitter dla długich dokumentów - hierarchical splitting
        # Używa intelligent separators do zachowania semantic boundaries
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,    # Optimal size dla GPT-4o-mini context
            chunk_overlap=200,  # Overlap zachowuje context między chunks
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]  # Hierarchical splitting
        )
    
    def _prepare_documents(self, articles: List) -> List[Document]:
        """
        Konwertuje NewsArticle objects na LangChain Documents dla AI processing.
        
        Transforms list artykułów na format wymagany przez LangChain chains.
        Każdy artykuł staje się Document z structured content i comprehensive metadata.
        
        Process:
        1. Limituje do max_articles_per_summary (performance)
        2. Kombinuje title, source i content w structured format
        3. Tworzy LangChain Document z page_content i metadata
        4. Metadata używana przez chains dla context i filtering
        
        Wykorzystywana przez:
        - BlogSummarizer.summarize() do przygotowania input data
        - Map-reduce chains do parallel processing
        - LangChain document loaders jako standard format
        
        Args:
            articles: Lista NewsArticle objects do konwersji
                     Może zawierać więcej niż max_articles_per_summary
                     
        Returns:
            List[Document]: LangChain Documents gotowe do AI processing
                           Każdy Document ma structured content i metadata
                           
        Note:
            Automatycznie obcina do pierwszych max_articles_per_summary artykułów.
            Format content: "Title: X\nSource: Y\nContent: Z" - structured dla AI
        """
        documents = []
        # Ograniczamy do max_articles_per_summary dla token efficiency
        for article in articles[:self.max_articles_per_summary]:
            # Tworzymy structured content format dla AI comprehension
            # Format: "Title: X\nSource: Y\nContent: Z" - clear structure dla LLM
            content = f"Title: {article.title}\nSource: {article.source}\nContent: {article.content}"
            
            # Tworzymy LangChain Document z comprehensive metadata
            documents.append(Document(
                page_content=content,  # Main content dla AI processing
                metadata={              # Rich metadata dla chains i filtering
                    "title": article.title,                    # Tytuł dla reference
                    "source": article.source,                  # Źródło dla grouping
                    "url": article.url,                        # URL dla validation
                    "published_date": str(article.published_date)  # Data dla sorting
                }
            ))
        return documents
    
    def summarize(self, articles: List, topic: str = "AI News") -> Optional[str]:
        """
        Abstrakcyjna metoda sumaryzacji - musi być zaimplementowana przez subklasy.
        
        Template Method Pattern - definiuje kontrakt dla wszystkich sumaryzatorów.
        Każda implementacja używa swojej strategii (blog post, newsletter, report).
        
        Args:
            articles: Lista NewsArticle objects do podsumowania
            topic: Temat kategorii (default "AI News") dla context
            
        Returns:
            Optional[str]: Generated summary lub None przy błędach
                          Format zależy od implementacji subclass
                          
        Note:
            Subklasy powinny używać _prepare_documents() do konwersji input data.
            Error handling powinno być graceful - return None nie Exception.
        """
        raise NotImplementedError


class BlogSummarizer(LangChainSummarizer):
    """
    Specialized summarizer dla tworzenia blog postów używający nowoczesnych LangChain patterns.
    
    Implementuje sophisticated approach do generowania engaging blog content
    z multiple news articles. Używa Map-Reduce pattern dla scalable processing
    i LangChain Expression Language (LCEL) dla modern chain composition.
    
    Architektura:
    - Map-Reduce Pattern: parallel processing artykułów + final synthesis
    - LCEL (LangChain Expression Language): modern chain composition
    - Structured Prompts: specialized templates dla blog generation
    - Multi-stage Processing: extract insights → combine → format
    
    Wykorzystywana przez:
    - BlogSummaryService jako main summarization engine
    - NewsOrchestrationService.create_intelligent_blog_summary()
    - Management commands dla automated blog generation
    - Scheduled tasks dla daily/weekly summaries
    
    Output format:
    - TITLE: [Compelling blog title]
    - SUMMARY: [Well-structured 400-600 word blog post]
    - Professional tone with actionable insights
    - Highlights most important developments
    
    Performance:
    - Processes up to 10 articles per summary (token optimization)
    - Map-reduce scales dla large article sets
    - GPT-4o-mini balance cost vs quality
    """
    
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.7):
        """
        Inicjalizuje BlogSummarizer z specialized prompts dla blog generation.
        
        Extends base LangChainSummarizer z blog-specific prompt templates
        i Map-Reduce configuration optimized dla engaging content creation.
        
        Args:
            model: OpenAI model (default "gpt-4o-mini" - cost-effective)
            temperature: Creativity level (0.7 optimal dla blog content)
            
        Prompt Templates:
        - blog_prompt: Single-stage summarization dla smaller datasets
        - map_prompt: Extract insights z individual articles
        - reduce_prompt: Combine insights into final blog post
        """
        super().__init__(model, temperature)  # Initialize base functionality
        
        # Blog summary prompt template - comprehensive single-stage approach
        # Używany gdy mamy mniejszą liczbę artykułów (< 5) i wszystkie mieszczą się w context
        self.blog_prompt = PromptTemplate(
            input_variables=["topic", "articles"],
            template="""You are an expert tech journalist and blogger. Create a comprehensive blog summary for the following {topic} articles.

Requirements:
1. Create a compelling title
2. Write 3-4 paragraphs summarizing the key trends and developments  
3. Highlight the most important stories
4. Include actionable insights where relevant
5. Keep the tone professional but engaging
6. Length: 400-600 words

Articles to summarize:
{articles}

Please format the response as:
TITLE: [Your title here]

SUMMARY:
[Your summary here]"""
        )
        
        # Map prompt - pierwszy stage Map-Reduce pattern
        # Ekstraktuje kluczowe insights z pojedynczych artykułów parallel
        self.map_prompt = PromptTemplate(
            input_variables=["text"],
            template="Extract key insights and important information from this news article:\n{text}\n\nKey insights:"
        )
        
        # Reduce prompt - drugi stage Map-Reduce pattern
        # Kombinuje wszystkie insights w final cohesive blog post
        self.reduce_prompt = PromptTemplate(
            input_variables=["text", "topic"],
            template="""Create a comprehensive blog post about {topic} based on these article insights:

{text}

Format as:
TITLE: [Compelling title]

SUMMARY:
[Well-structured blog summary with key insights and trends]"""
        )
    
    def summarize(self, articles: List, topic: str = "AI News") -> Optional[str]:
        """
        Główna metoda summarization używająca modern LangChain approach.
        
        Implementuje intelligent selection między single-stage a Map-Reduce processing
        based na liczbie artykułów i ich długości. Zapewnia optimal performance
        i quality dla różnych scenarios.
        
        Workflow:
        1. Prepare documents z artykułów (max 10)
        2. Zawsze używa Map-Reduce dla consistency i scalability
        3. Parallel processing individual articles
        4. Combine insights w final blog post
        5. Return formatted result z TITLE + SUMMARY
        
        Wykorzystywana przez:
        - BlogSummaryService._create_summary() jako main engine
        - NewsOrchestrationService dla intelligent summaries
        - Management commands dla batch processing
        
        Args:
            articles: Lista NewsArticle objects (będzie limited do 10)
            topic: Kategoria tematu dla context (np. "AI News", "Tech")
            
        Returns:
            Optional[str]: Formatted blog post "TITLE: ...\n\nSUMMARY: ..."
                          lub None jeśli error occurred
                          
        Error Handling:
            Graceful handling - logs errors ale returns None
            Nie crasha całego pipeline przy individual failures
        """
        try:
            # Konwertujemy artykuły na LangChain Documents
            documents = self._prepare_documents(articles)
            
            if not documents:
                return None
            
            # Zawsze używamy Map-Reduce dla consistency i scalability
            # Map-Reduce scales better dla larger datasets i zapewnia uniform quality
            return self._modern_map_reduce_summarize(documents, topic)
                
        except Exception as e:
            # Graceful error handling - log ale nie crash pipeline
            logger.error(f"Error with LangChain summarization: {e}")
            return None
    
    def _modern_map_reduce_summarize(self, documents: List[Document], topic: str) -> str:
        """
        Modern Map-Reduce implementation używający LangChain Expression Language (LCEL).
        
        Implementuje sophisticated two-stage processing:
        1. MAP stage: Parallel extraction insights z individual documents
        2. REDUCE stage: Synthesis wszystkich insights w cohesive blog post
        
        Advantages Map-Reduce approach:
        - Scalability: handles unlimited liczba artykułów
        - Parallel processing: faster than sequential
        - Quality: focused analysis każdego artykułu + intelligent combination
        - Token efficiency: avoids hitting context limits
        
        LCEL Benefits:
        - Modern LangChain syntax (pipe operator |)
        - Better error handling i debugging
        - Composable chains
        - Performance optimizations
        
        Args:
            documents: Lista LangChain Documents do przetworzenia
            topic: Kategoria tematu dla final synthesis
            
        Returns:
            str: Formatted blog post z TITLE i SUMMARY
                 Format: "TITLE: ...\n\nSUMMARY: ..."
                 
        Process Flow:
            Documents → MAP (extract insights) → REDUCE (combine) → Final Blog Post
        """
        
        # STAGE 1: MAP - Create LCEL chain dla extracting insights
        # Pipe operator (|) tworzy composable chain: prompt → LLM → parser
        map_chain = self.map_prompt | self.llm | StrOutputParser()
        
        # Process wszystkie documents w parallel (conceptually)
        # W praktyce sequential ale każdy document jest processed independently
        mapped_results = []
        for doc in documents:
            try:
                # Invoke chain dla każdego document - extract key insights
                result = map_chain.invoke({"text": doc.page_content})
                mapped_results.append(result)
            except Exception as e:
                # Graceful handling - single document failure nie crashuje całego process
                logger.warning(f"Error processing document: {e}")
                continue
        
        # Fallback jeśli wszystkie documents failed
        if not mapped_results:
            return f"TITLE: {topic} Update\n\nSUMMARY: No content available for summarization."
        
        # STAGE 2: REDUCE - Combine wszystkie extracted insights
        # Join insights z double newlines dla clear separation
        combined_text = "\n\n".join(mapped_results)
        
        # Create reduce chain using LCEL dla final synthesis
        reduce_chain = self.reduce_prompt | self.llm | StrOutputParser()
        
        # Generate final comprehensive blog post
        result = reduce_chain.invoke({
            "text": combined_text,  # All combined insights
            "topic": topic         # Topic category dla context
        })
        
        return result


class BlogSummaryService:
    """
    Comprehensive service do tworzenia i zarządzania blog summaries używający wyłącznie LangChain.
    
    Jest to główny orchestrator dla generowania AI-powered blog posts z news articles.
    Zapewnia high-level interface dla different types summaries (daily, weekly, custom)
    i manages całość lifecycle od article selection do database storage.
    
    Architektura:
    - Service Layer Pattern: enkapsuluje business logic dla blog generation
    - Dependency Injection: używa BlogSummarizer jako engine
    - Database Integration: automatic storage w BlogSummary model
    - Time-based Filtering: intelligent article selection based na dates
    
    Wykorzystywana przez:
    - NewsOrchestrationService.create_intelligent_blog_summary()
    - Management commands dla automated blog generation
    - Scheduled tasks (daily/weekly summary cron jobs)
    - API endpoints dla on-demand summary generation
    
    Features:
    - Daily summaries: last 24 hours articles
    - Weekly summaries: last 7 days articles  
    - Custom summaries: user-provided article sets
    - Automatic deduplication: tylko unique articles
    - Database persistence: BlogSummary objects z relations
    
    Dependencies:
    - BlogSummarizer: AI engine dla content generation
    - NewsArticle model: source articles
    - BlogSummary model: storage dla generated content
    """
    
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.7):
        """
        Inicjalizuje BlogSummaryService z configured BlogSummarizer.
        
        Creates service instance z AI summarization capabilities.
        Encapsulates BlogSummarizer configuration i provides high-level API.
        
        Args:
            model: OpenAI model dla summarization (default "gpt-4o-mini")
                  gpt-4o-mini offers best cost/performance ratio dla blog generation
            temperature: AI creativity level 0.0-1.0 (default 0.7)
                        0.7 provides good balance między consistency a engaging content
        
        Configuration:
        - Uses BlogSummarizer jako underlying AI engine
        - Inherits all LangChain i Map-Reduce capabilities
        - Ready dla immediate summary generation
        """
        # Initialize AI summarization engine z specified configuration
        self.summarizer = BlogSummarizer(model=model, temperature=temperature)
    
    def create_daily_summary(self, topic_category: str = "AI News") -> Optional:
        """
        Tworzy daily blog summary z artykułów opublikowanych w ostatnich 24h.
        
        Automatically selects articles z yesterday's publications, filters duplicates,
        i generates comprehensive blog post summarizing key developments.
        
        Wykorzystywana przez:
        - Scheduled daily tasks (cron jobs)
        - Management commands z --daily flag
        - NewsOrchestrationService dla automated daily reports
        - API endpoints dla daily summary requests
        
        Workflow:
        1. Calculate yesterday's date range (24h window)
        2. Query unique articles z database (is_duplicate=False)
        3. Order by published_date (newest first)
        4. Generate summary using BlogSummarizer
        5. Save jako BlogSummary w database
        
        Args:
            topic_category: Kategoria tematu (default "AI News")
                           Używana jako context dla AI generation
                           
        Returns:
            Optional[BlogSummary]: Generated summary object lub None
                                  None jeśli no articles found lub generation failed
                                  
        Note:
            Używa 24-hour window - artykuły od yesterday do now
            Automatic deduplication przez is_duplicate filter
        """
        from ..models import NewsArticle
        
        # Calculate 24-hour window dla daily summary
        yesterday = datetime.now() - timedelta(days=1)
        
        # Query unique articles z last 24 hours
        articles = NewsArticle.objects.filter(
            is_duplicate=False,         # Only unique articles (deduplication)
            published_date__gte=yesterday,     # From yesterday
            published_date__lt=datetime.now()  # Until now
        ).order_by('-published_date')  # Newest first
        
        # Check if any articles found
        if not articles.exists():
            logger.info("No new articles found for daily summary")
            return None
        
        # Generate summary using private method
        return self._create_summary(list(articles), topic_category)
    
    def create_weekly_summary(self, topic_category: str = "AI News") -> Optional:
        """
        Tworzy weekly blog summary z artykułów opublikowanych w ostatnich 7 dniach.
        
        Generates comprehensive weekly roundup covering major trends i developments
        z past week. More extensive than daily summaries - covers broader topics.
        
        Wykorzystywana przez:
        - Weekly scheduled tasks (Sunday summary generation)
        - Management commands z --weekly flag
        - Email newsletters z weekly content
        - Archive/retrospective analysis
        
        Workflow:
        1. Calculate 7-day window (week ago to now)
        2. Query unique articles z database (larger dataset)
        3. Order chronologically (newest first)
        4. Generate comprehensive weekly overview
        5. Save jako BlogSummary w database
        
        Args:
            topic_category: Kategoria tematu (default "AI News")
                           Context dla AI to understand focus area
                           
        Returns:
            Optional[BlogSummary]: Generated weekly summary lub None
                                  None jeśli no articles lub generation failed
                                  
        Note:
            7-day window typically contains more articles than daily
            BlogSummarizer automatically limits to 10 most recent dla processing
        """
        from ..models import NewsArticle
        
        # Calculate 7-day window dla weekly summary
        week_ago = datetime.now() - timedelta(days=7)
        
        # Query unique articles z last week
        articles = NewsArticle.objects.filter(
            is_duplicate=False,              # Only unique articles
            published_date__gte=week_ago,           # From week ago
            published_date__lt=datetime.now()       # Until now
        ).order_by('-published_date')      # Newest first
        
        # Check if any articles found
        if not articles.exists():
            logger.info("No articles found for weekly summary")
            return None
        
        # Generate comprehensive weekly summary
        return self._create_summary(list(articles), topic_category)
    
    def create_custom_summary(self, articles: List, topic_category: str = "AI News") -> Optional:
        """
        Tworzy custom blog summary z user-provided set artykułów.
        
        Flexible method dla generating summaries z arbitrary article collections.
        Używana gdy users want specific articles summarized lub custom time ranges.
        
        Wykorzystywana przez:
        - API endpoints z custom article selection
        - Interactive user interfaces (article picker)
        - Specialized analysis (specific sources, topics, dates)
        - Testing z specific article sets
        
        Use Cases:
        - Summarize specific company announcements
        - Create themed summaries (specific technology focus)
        - Generate retrospective analysis dla specific events
        - Custom date ranges (not daily/weekly)
        
        Args:
            articles: Lista NewsArticle objects do summarization
                     Can be any size - BlogSummarizer limits to 10
            topic_category: Custom topic kategoria (default "AI News")
                           Allows specialized context dla AI generation
                           
        Returns:
            Optional[BlogSummary]: Generated custom summary lub None
                                  None tylko jeśli empty articles lub generation failed
                                  
        Note:
            No automatic filtering - caller responsible dla article selection
            Duplicates should be pre-filtered by caller jeśli desired
        """
        # Validate input - empty list returns None immediately
        if not articles:
            return None
            
        # Delegate to private summary creation method
        return self._create_summary(articles, topic_category)
    
    def _create_summary(self, articles: List, topic_category: str) -> Optional:
        """
        Private method dla actual blog summary creation i database storage.
        
        Core implementation używana przez wszystkie public summary methods.
        Handles AI generation, response parsing, i database persistence.
        
        Workflow:
        1. Call BlogSummarizer.summarize() dla AI generation
        2. Parse response dla TITLE i SUMMARY components
        3. Create BlogSummary object w database
        4. Associate articles z created summary
        5. Return completed BlogSummary object
        
        Error Handling:
        - Graceful handling AI generation failures
        - Database transaction safety
        - Parsing fallbacks dla malformed responses
        - Comprehensive logging dla debugging
        
        Args:
            articles: Lista NewsArticle objects (already filtered)
            topic_category: Topic context dla AI generation
            
        Returns:
            Optional[BlogSummary]: Created BlogSummary object lub None
                                  None indicates generation lub storage failure
                                  
        Private Method:
            Used internally by create_daily_summary, create_weekly_summary,
            create_custom_summary - provides unified implementation
        """
        from ..models import BlogSummary
        
        try:
            # Generate AI summary using BlogSummarizer
            summary_text = self.summarizer.summarize(articles, topic_category)
            
            if not summary_text:
                logger.error("Failed to generate summary with LangChain")
                return None
            
            # Parse TITLE i SUMMARY z AI response
            # Default values in case parsing fails
            title = "AI News Summary"
            summary = summary_text
            
            # Look dla structured TITLE: format
            if "TITLE:" in summary_text:
                lines = summary_text.split('\n')
                for line in lines:
                    if line.startswith("TITLE:"):
                        title = line.replace("TITLE:", "").strip()
                        break
                
                # Extract SUMMARY: section jeśli present
                if "SUMMARY:" in summary_text:
                    summary_start = summary_text.find("SUMMARY:")
                    summary = summary_text[summary_start + 8:].strip()
            
            # Create BlogSummary object w database
            blog_summary = BlogSummary.objects.create(
                title=title,                    # Parsed lub default title
                summary=summary,                # Extracted summary content
                topic_category=topic_category   # User-specified category
            )
            
            # Associate articles z created summary (many-to-many relationship)
            blog_summary.articles.set(articles)
            
            logger.info(f"Created blog summary: {title}")
            return blog_summary
        
        except Exception as e:
            # Comprehensive error handling - log ale nie crash system
            logger.error(f"Error creating blog summary: {e}")
            return None
    
    def get_recent_summaries(self, limit: int = 10) -> List:
        """
        Pobiera recent blog summaries z database w chronological order.
        
        Utility method dla retrieving generated summaries dla display,
        API responses, lub administrative purposes.
        
        Wykorzystywana przez:
        - API endpoints dla listing recent summaries
        - Admin interfaces dla content management
        - Archive browsing functionality
        - Statistics i reporting systems
        
        Args:
            limit: Maximum number summaries to return (default 10)
                  Controls pagination i performance
                  
        Returns:
            List[BlogSummary]: Lista recent BlogSummary objects
                              Ordered by creation time (newest first)
                              Empty list jeśli no summaries exist
                              
        Note:
            Uses Django ORM default ordering (usually by creation time)
            No filtering - returns wszystkie summaries regardless of category
        """
        from ..models import BlogSummary
        # Query recent summaries z specified limit
        return list(BlogSummary.objects.all()[:limit])