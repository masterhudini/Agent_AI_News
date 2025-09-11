from typing import List, Dict, Optional, Any
import logging
from datetime import datetime
from django.conf import settings

# LangChain imports - updated for Python 3.12 and latest versions
from langchain.chains.llm import LLMChain
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnablePassthrough
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.tools import tool
from langchain_core.messages import SystemMessage

# Pydantic for structured output
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class NewsAnalysisResult(BaseModel):
    """
    Pydantic model dla strukturalnego outputu z analizy newsowych artykułów przez AI.
    
    Definiuje standardowy format wyników analizy artykułów używany przez NewsAnalyzer.
    Wszystkie pola są walidowane przez Pydantic i zapewniają type safety oraz
    consistent data structure przez cały system.
    
    Wykorzystywana przez:
    - NewsAnalyzer.analyze_article() jako return type
    - LangChain PydanticOutputParser dla structured extraction
    - Database storage structured analysis results
    - API endpoints dla consistent response format
    
    Fields:
    - key_topics: Lista głównych tematów/trendów w artykule
    - importance_score: Numeryczna ocena ważności 0.0-1.0
    - category: Kategoryzacja artykułu (AI, Tech, Business, etc.)
    - summary: Krótkie streszczenie w 2-3 zdaniach
    
    Pydantic Features:
    - Field validation (importance_score between 0.0-1.0)
    - Automatic JSON serialization/deserialization
    - Type hints dla IDE support
    - Documentation strings dla OpenAPI/schema generation
    """
    key_topics: List[str] = Field(description="List of main topics/themes")
    importance_score: float = Field(ge=0.0, le=1.0, description="Importance score from 0.0 to 1.0")
    category: str = Field(description="News category: AI, Tech, Business, etc.")
    summary: str = Field(description="Brief summary of the article")


class BlogPostStructure(BaseModel):
    """
    Pydantic model dla strukturalnego formatu generowanych blog postów przez AI.
    
    Definiuje standardową strukturę blog postów tworzonych przez BlogGenerator.
    Zapewnia consistent format i quality przez wszystkie generated content,
    ułatwiając automated publishing i content management.
    
    Wykorzystywana przez:
    - BlogGenerator.generate_blog_post() jako return type
    - LangChain structured output parsing
    - Content management systems dla automated publishing
    - API responses dla blog generation endpoints
    
    Structure:
    - title: Compelling, SEO-friendly tytuł
    - introduction: Hook paragraph engaging readers
    - main_content: Core content z insights i analysis
    - conclusion: Summary z key takeaways
    - tags: Lista tagów dla SEO i categorization
    
    Content Guidelines:
    - Title: Clear, compelling, SEO-optimized
    - Introduction: Hook reader, set context
    - Main content: 800-1200 words, well-structured
    - Conclusion: Actionable takeaways, future outlook
    - Tags: Relevant keywords dla discoverability
    """
    title: str = Field(description="Compelling blog post title")
    introduction: str = Field(description="Engaging introduction paragraph")
    main_content: str = Field(description="Main content with key insights")
    conclusion: str = Field(description="Conclusion with takeaways")
    tags: List[str] = Field(description="Relevant tags for the post")


class NewsAnalyzer:
    """
    Inteligentny analyzer artykułów newsowych wykorzystujący OpenAI GPT dla structured analysis.
    
    Implementuje sophisticated NLP analysis pipeline używając LangChain i OpenAI
    do ekstraktowania structured insights z news articles. Generates consistent,
    machine-readable analysis results które mogą być używane przez inne system components.
    
    Architektura:
    - LCEL (LangChain Expression Language): Modern chain composition
    - Structured Output: Pydantic models dla type-safe results
    - Template-based Prompts: Consistent analysis approach
    - Error Recovery: Graceful handling malformed responses
    
    Wykorzystywana przez:
    - LangChainNewsOrchestrator.process_articles_with_analysis()
    - Management commands dla batch article analysis
    - API endpoints dla on-demand article insights
    - Research tools dla trend analysis
    
    Analysis Capabilities:
    - Topic Extraction: Identifies key themes i trends
    - Importance Scoring: Quantifies article significance 0.0-1.0
    - Categorization: AI, Tech, Business, Science classification
    - Summarization: Concise 2-3 sentence summaries
    
    Performance:
    - GPT-4o-mini: Cost-effective dla batch processing
    - Temperature 0.3: Consistent, factual analysis
    - Content limit: 2000 chars dla token optimization
    """
    
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.3):
        """
        Inicjalizuje NewsAnalyzer z OpenAI model i structured output parsing.
        
        Konfiguruje LLM, prompt templates i LCEL chain dla automated analysis.
        Uses Pydantic parser dla structured extraction consistent results.
        
        Args:
            model: OpenAI model name (default "gpt-4o-mini")
                  gpt-4o-mini offers best cost/performance dla analysis tasks
            temperature: Randomness level 0.0-1.0 (default 0.3)
                        Low temperature ensures consistent, factual analysis
        
        Components:
        - ChatOpenAI LLM z specified configuration
        - PydanticOutputParser dla NewsAnalysisResult extraction
        - PromptTemplate z comprehensive analysis instructions
        - LCEL chain combining prompt → LLM → parser
        
        Note:
            Używa wyłącznie OpenAI - no fallback models dla consistency
        """
        # Initialize OpenAI LLM - exclusively OpenAI, no fallbacks dla consistency
        from ..core.config import get_app_config
        config = get_app_config()
        self.llm = ChatOpenAI(
            api_key=config.openai_api_key,  # Configuration management integration
            model=model,            # Default: gpt-4o-mini (cost-effective)
            temperature=temperature  # Low temp dla factual, consistent analysis
        )
        
        # Set up structured output parser dla type-safe results
        # PydanticOutputParser automatically generates format instructions
        self.output_parser = PydanticOutputParser(pydantic_object=NewsAnalysisResult)
        
        # Comprehensive analysis prompt template z clear instructions
        # Uses partial_variables dla automatic format instruction injection
        self.analysis_prompt = PromptTemplate(
            input_variables=["title", "content", "source"],  # Required variables
            template="""Analyze the following news article and provide structured insights:

Title: {title}
Source: {source}
Content: {content}

Please analyze the article and provide:
1. Key topics/themes (list of main topics)
2. Importance score (0.0 to 1.0 based on significance)
3. Category (AI, Tech, Business, Science, etc.)
4. Brief summary (2-3 sentences)

{format_instructions}""",
            partial_variables={"format_instructions": self.output_parser.get_format_instructions()}
        )
        
        # Create LCEL chain: prompt → LLM → structured parser
        # Modern LangChain pattern z pipe operator
        self.analysis_chain = self.analysis_prompt | self.llm | self.output_parser
    
    def analyze_article(self, article) -> NewsAnalysisResult:
        """
        Analizuje pojedynczy news article i zwraca structured insights.
        
        Main method dla article analysis - takes NewsArticle object,
        processes it through AI analysis chain, i returns structured results.
        
        Workflow:
        1. Extract article data (title, content, source)
        2. Limit content length dla token optimization
        3. Invoke LCEL analysis chain
        4. Return structured NewsAnalysisResult
        5. Fallback to default result on errors
        
        Wykorzystywana przez:
        - LangChainNewsOrchestrator.process_articles_with_analysis()
        - Batch processing commands
        - Real-time article analysis APIs
        - Research i trend analysis tools
        
        Args:
            article: NewsArticle object z title, content, source fields
                    Expects standard NewsArticle model structure
                    
        Returns:
            NewsAnalysisResult: Structured analysis z key_topics, importance_score,
                               category, i summary fields
                               Default fallback values on processing errors
                               
        Error Handling:
            Graceful fallback - returns default NewsAnalysisResult on failures
            Logs errors ale doesn't crash calling code
            
        Performance:
            Content limited to 2000 chars dla token efficiency
        """
        try:
            # Invoke LCEL analysis chain z structured input
            result = self.analysis_chain.invoke({
                "title": article.title,
                "content": article.content[:2000],  # Limit dla token optimization
                "source": article.source
            })
            return result
        except Exception as e:
            # Graceful error handling - log ale return sensible defaults
            logger.error(f"Error analyzing article {article.title}: {e}")
            
            # Return default NewsAnalysisResult instead of crashing
            return NewsAnalysisResult(
                key_topics=["news"],        # Generic topic
                importance_score=0.5,       # Neutral importance
                category="General",          # Broad category
                summary=article.title       # Use title as fallback summary
            )


class BlogGenerator:
    """
    Zaawansowany generator blog postów wykorzystujący OpenAI GPT dla high-quality content creation.
    
    Specialized AI system dla tworzenia engaging, well-structured blog posts
    z multiple news articles. Uses sophisticated prompting i structured output
    do generowania professional-grade content ready dla publication.
    
    Architektura:
    - LCEL Chain Composition: Modern LangChain patterns
    - Structured Output: Pydantic BlogPostStructure dla consistency
    - Content Intelligence: AI-driven insights i analysis
    - Multi-article Synthesis: Combines insights z multiple sources
    
    Wykorzystywana przez:
    - LangChainNewsOrchestrator.create_intelligent_blog_post()
    - BlogSummaryService jako alternative engine
    - Content management systems dla automated publishing
    - Editorial workflows dla content creation
    
    Content Features:
    - Compelling titles optimized dla engagement
    - Structured format: intro → main content → conclusion
    - Professional tone appropriate dla target audience
    - Actionable insights i practical takeaways
    - SEO-friendly tags dla discoverability
    
    Quality Standards:
    - 800-1200 words optimal length
    - Clear structure z logical flow
    - Evidence-based insights z source articles
    - Engaging writing style
    """
    
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.7):
        """
        Inicjalizuje BlogGenerator z OpenAI configuration i structured output parsing.
        
        Sets up LLM, prompt templates i LCEL chain dla automated blog generation.
        Higher temperature than analyzer dla more creative, engaging content.
        
        Args:
            model: OpenAI model (default "gpt-4o-mini")
                  gpt-4o-mini balances quality z cost dla content generation
            temperature: Creativity level 0.0-1.0 (default 0.7)
                        Higher temp dla more engaging, varied writing style
        
        Components:
        - ChatOpenAI LLM configured dla creative content
        - PydanticOutputParser dla BlogPostStructure extraction
        - Comprehensive blog prompt z detailed instructions
        - LCEL chain dla streamlined generation
        
        Creative vs Analytical:
        - Higher temperature (0.7) vs analyzer (0.3)
        - Focus na engaging content vs factual analysis
        - Structured output maintains consistency despite creativity
        """
        # Initialize OpenAI LLM - exclusively OpenAI dla consistent creative output
        from ..core.config import get_app_config
        config = get_app_config()
        self.llm = ChatOpenAI(
            api_key=config.openai_api_key,  # Configuration management
            model=model,            # Default: gpt-4o-mini
            temperature=temperature  # 0.7 dla creative, engaging content
        )
        
        # Structured output parser dla consistent blog post format
        # BlogPostStructure ensures all required sections are generated
        self.output_parser = PydanticOutputParser(pydantic_object=BlogPostStructure)
        
        # Comprehensive blog generation prompt z detailed content guidelines
        # Includes target audience customization dla appropriate tone
        self.blog_prompt = PromptTemplate(
            input_variables=["topic", "articles_summary", "target_audience"],
            template="""Create a comprehensive blog post about {topic} for {target_audience}.

Based on these article summaries:
{articles_summary}

Generate a well-structured blog post with:
1. A compelling title that captures attention
2. An engaging introduction that hooks the reader
3. Main content with key insights, trends, and analysis
4. A conclusion with key takeaways and future outlook
5. Relevant tags for categorization

Make it informative, engaging, and professional. Length should be 800-1200 words.

{format_instructions}""",
            partial_variables={"format_instructions": self.output_parser.get_format_instructions()}
        )
        
        # LCEL chain: prompt → LLM → structured parser
        self.blog_chain = self.blog_prompt | self.llm | self.output_parser
    
    def generate_blog_post(self, topic: str, articles: List, target_audience: str = "tech professionals") -> BlogPostStructure:
        """
        Generuje comprehensive blog post z provided articles i topic.
        
        Main method dla blog generation - combines multiple articles into
        cohesive, well-structured blog post targeted dla specific audience.
        
        Process:
        1. Prepare article summaries (limited to 10 articles)
        2. Truncate content dla token optimization
        3. Invoke LCEL blog generation chain
        4. Return structured BlogPostStructure
        5. Fallback to template structure on errors
        
        Wykorzystywana przez:
        - LangChainNewsOrchestrator.create_intelligent_blog_post()
        - Content management systems
        - Automated blog generation workflows
        - API endpoints dla on-demand content
        
        Args:
            topic: Main topic/theme dla blog post (np. "AI News", "Tech Trends")
            articles: Lista NewsArticle objects jako source material
                     Limited to first 10 dla token efficiency
            target_audience: Audience type dla tone customization
                           (default "tech professionals")
                           
        Returns:
            BlogPostStructure: Complete blog post z title, introduction,
                              main_content, conclusion, i tags
                              Fallback template structure on errors
                              
        Error Handling:
            Graceful fallback - returns basic template structure
            Comprehensive error logging
            
        Content Optimization:
            Article content truncated to 200 chars per article
            Maximum 10 articles processed dla token limits
        """
        try:
            # Prepare structured articles summary dla AI processing
            articles_summary = []
            for article in articles[:10]:  # Limit to 10 articles dla token efficiency
                # Format: bullet point z title, source, i truncated content
                summary = f"- {article.title} ({article.source}): {article.content[:200]}..."
                articles_summary.append(summary)
            
            # Join wszystkie summaries w single text block
            articles_text = "\n".join(articles_summary)
            
            # Invoke LCEL blog generation chain
            result = self.blog_chain.invoke({
                "topic": topic,                    # Main theme
                "articles_summary": articles_text, # Source material
                "target_audience": target_audience # Tone customization
            })
            
            return result
            
        except Exception as e:
            # Graceful error handling - return template structure
            logger.error(f"Error generating blog post: {e}")
            return BlogPostStructure(
                title=f"{topic} - Latest Updates",                      # Generic title
                introduction=f"Here are the latest updates in {topic}:", # Basic intro
                main_content="Recent developments and insights...",      # Placeholder content
                conclusion="Stay tuned for more updates.",              # Generic conclusion
                tags=[topic.lower(), "news", "tech"]                   # Basic tags
            )


class NewsProcessingAgent:
    """
    Inteligentny conversational agent dla interactive news data queries używający LangChain Agents.
    
    Advanced AI agent z access do specialized tools dla querying, analyzing,
    i reporting na news database. Uses OpenAI Functions approach dla reliable
    tool calling i natural language interaction.
    
    Architektura:
    - OpenAI Functions Agent: Reliable tool selection i execution
    - Tool-based Architecture: Modular capabilities through @tool decorators
    - AgentExecutor: Orchestrates conversation flow i tool usage
    - Error Recovery: Graceful handling tool failures
    
    Tools Available:
    - search_articles(): Semantic search using vector database
    - get_article_stats(): Database statistics i metrics
    - analyze_trends(): Topic-based trend analysis
    
    Wykorzystywana przez:
    - LangChainNewsOrchestrator.interactive_news_query()
    - Management commands z --interactive mode
    - Chat interfaces dla news exploration
    - Research tools dla data analysis
    
    Capabilities:
    - Natural language queries about news data
    - Statistical analysis i reporting
    - Trend identification i analysis
    - Article search i discovery
    - Interactive data exploration
    
    Agent Pattern Benefits:
    - Dynamic tool selection based na user query
    - Multi-step reasoning i planning
    - Context-aware responses
    - Extensible through additional tools
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Inicjalizuje NewsProcessingAgent z OpenAI Functions agent i specialized tools.
        
        Creates conversational AI agent z access do news database operations.
        Sets up tools, system prompt, i agent executor dla interactive queries.
        
        Args:
            model: OpenAI model dla agent reasoning (default "gpt-4o-mini")
                  gpt-4o-mini provides good balance dla agent tasks
                  
        Components:
        - ChatOpenAI LLM z moderate temperature (0.5)
        - Custom tools decorated z @tool dla news operations
        - SystemMessage defining agent behavior
        - OpenAI Functions Agent dla reliable tool calling
        - AgentExecutor dla conversation management
        
        Agent Configuration:
        - Temperature 0.5: Balance reasoning z consistency
        - Verbose mode: Detailed logging dla debugging
        - System prompt: Clear role definition
        """
        # Initialize LLM dla agent reasoning
        from ..core.config import get_app_config
        config = get_app_config()
        self.llm = ChatOpenAI(
            api_key=config.openai_api_key,
            model=model,            # Default: gpt-4o-mini
            temperature=0.5         # Balanced reasoning vs consistency
        )
        
        # Create specialized tools using modern @tool decorator approach
        self.tools = self._create_tools()
        
        # Define agent system prompt - clear role i capabilities
        system_message = SystemMessage(
            content="You are a helpful assistant for analyzing news data. Use the available tools to answer questions about news articles, statistics, and trends."
        )
        
        # Create OpenAI Functions agent - most reliable dla tool calling
        self.agent = create_openai_functions_agent(self.llm, self.tools, system_message)
        
        # AgentExecutor orchestrates conversation i tool execution
        self.agent_executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True)
    
    def _create_tools(self):
        """
        Creates specialized tools dla news database operations using @tool decorators.
        
        Modern LangChain approach - each tool jest decorated function z
        clear docstring describing its capabilities. Agent automatically
        selects appropriate tools based na user queries.
        
        Tools Created:
        - search_articles(): Vector-based semantic search
        - get_article_stats(): Database statistics i metrics  
        - analyze_trends(): Topic-based trend analysis
        
        Tool Pattern Benefits:
        - Clear function signatures dla agent understanding
        - Comprehensive docstrings dla tool selection
        - Error handling within each tool
        - Modular i extensible architecture
        
        Returns:
            List: Lista tool objects ready dla agent use
                 Each tool jest callable z error handling
                 
        Note:
            Uses nested function definitions dla access do class dependencies
            All tools handle errors gracefully i return string responses
        """
        
        @tool
        def search_articles(query: str) -> str:
            """
            Search for articles semantically similar to query using vector database.
            
            Uses DuplicationService vector search capabilities dla finding
            articles related to user's query. Returns formatted list of matches.
            """
            try:
                from .deduplication import DuplicationService
                service = DuplicationService()
                # Semantic search using vector embeddings
                articles = service.search_similar_content(query, limit=5)
                
                if not articles:
                    return "No similar articles found."
                
                # Format results dla readable output
                results = []
                for article in articles:
                    results.append(f"- {article.title} ({article.source})")
                
                return f"Found {len(articles)} similar articles:\n" + "\n".join(results)
            except Exception as e:
                return f"Error searching articles: {e}"
        
        @tool 
        def get_article_stats() -> str:
            """
            Get comprehensive statistics about articles in the database.
            
            Provides overview of database contents including total articles,
            unique articles (after deduplication), i number of sources.
            """
            try:
                from ..models import NewsArticle
                # Database queries dla comprehensive stats
                total = NewsArticle.objects.count()
                unique = NewsArticle.objects.filter(is_duplicate=False).count()
                sources = NewsArticle.objects.values_list('source', flat=True).distinct().count()
                
                return f"Database stats: {total} total articles, {unique} unique, {sources} sources"
            except Exception as e:
                return f"Error getting stats: {e}"
        
        @tool
        def analyze_trends(topic: str) -> str:
            """
            Analyze recent trends for a specific topic over the last week.
            
            Searches article titles dla topic mentions i counts occurrences
            w recent time period dla trend analysis.
            """
            try:
                from ..models import NewsArticle
                from datetime import timedelta, datetime
                
                # Calculate week window dla trend analysis
                week_ago = datetime.now() - timedelta(days=7)
                recent_articles = NewsArticle.objects.filter(
                    title__icontains=topic,        # Topic search w titles
                    published_date__gte=week_ago,   # Last week only
                    is_duplicate=False              # Unique articles only
                ).count()
                
                return f"Found {recent_articles} articles about '{topic}' in the last week"
            except Exception as e:
                return f"Error analyzing trends: {e}"
        
        # Return lista wszystkich created tools
        return [search_articles, get_article_stats, analyze_trends]
    
    def process_request(self, request: str) -> str:
        """
        Processes natural language request about news data using agent capabilities.
        
        Main interface dla interactive queries - agent analyzes request,
        selects appropriate tools, i provides comprehensive response.
        
        Workflow:
        1. Agent analyzes user request
        2. Selects appropriate tools (search, stats, trends)
        3. Executes tool calls w proper sequence
        4. Synthesizes results into coherent response
        5. Returns formatted answer
        
        Wykorzystywana przez:
        - LangChainNewsOrchestrator.interactive_news_query()
        - Interactive CLI interfaces
        - Chat APIs dla news exploration
        - Research i analysis workflows
        
        Args:
            request: Natural language query about news data
                    Examples: "Find articles about AI", "What are the stats?",
                             "Analyze trends for machine learning"
                             
        Returns:
            str: Comprehensive response based na tool execution
                Formatted answer combining tool results
                Error message jeśli agent execution fails
                
        Agent Capabilities:
        - Multi-step reasoning dla complex queries
        - Tool selection based na query content
        - Context-aware responses
        - Error recovery i graceful degradation
        """
        try:
            # Invoke agent executor z user request
            response = self.agent_executor.invoke({"input": request})
            # Extract output z agent response
            return response.get("output", "No response generated")
        except Exception as e:
            # Comprehensive error handling - log i return user-friendly message
            logger.error(f"Error processing agent request: {e}")
            return f"Sorry, I encountered an error: {e}"


class LangChainNewsOrchestrator:
    """
    Główny orchestrator dla comprehensive LangChain-based news processing operations.
    
    High-level koordinator łączący wszystkie LangChain components w unified system
    dla advanced news processing, analysis, i content generation. Provides
    simplified API dla complex AI-powered news operations.
    
    Architektura:
    - Service Composition: Combines NewsAnalyzer, BlogGenerator, NewsProcessingAgent
    - Unified API: Single interface dla multiple AI capabilities
    - Error Orchestration: Coordinates error handling across components
    - Workflow Management: Manages complex multi-step AI processes
    
    Components:
    - NewsAnalyzer: Structured article analysis
    - BlogGenerator: AI-powered blog post creation
    - NewsProcessingAgent: Interactive conversational queries
    
    Wykorzystywana przez:
    - NewsOrchestrationService jako AI processing engine
    - Management commands dla advanced AI operations
    - API endpoints requiring sophisticated AI capabilities
    - Research tools i analytics workflows
    
    Core Capabilities:
    - Bulk article analysis z structured outputs
    - Intelligent blog post generation z multiple sources
    - Interactive querying i data exploration
    - End-to-end content creation workflows
    
    Integration Pattern:
    - Consistent model configuration across all components
    - Unified error handling i logging
    - Structured output formats dla seamless integration
    - Scalable architecture dla production workloads
    """
    
    def __init__(self, model_type: str = "openai", model: str = "gpt-4o-mini"):
        """
        Inicjalizuje LangChainNewsOrchestrator z all AI components.
        
        Creates integrated system z NewsAnalyzer, BlogGenerator, i NewsProcessingAgent
        wszystkich używających consistent model configuration.
        
        Args:
            model_type: Type of model provider (currently only "openai")
                       Placeholder dla future multi-provider support
            model: Specific model name (default "gpt-4o-mini")
                  Consistent model across all components dla uniform quality
                  
        Architecture:
        - Single model configuration dla all components
        - Consistent behavior across different AI operations
        - Unified initialization i error handling
        
        Component Configuration:
        - NewsAnalyzer: Low temperature (0.3) dla factual analysis
        - BlogGenerator: Medium temperature (0.7) dla creative content
        - NewsProcessingAgent: Balanced temperature (0.5) dla reasoning
        """
        # Initialize all AI components z consistent model configuration
        # Only OpenAI models - no fallbacks dla consistent behavior
        self.analyzer = NewsAnalyzer(model=model)           # Factual analysis
        self.blog_generator = BlogGenerator(model=model)    # Creative content
        self.agent = NewsProcessingAgent(model=model)       # Interactive queries
    
    def process_articles_with_analysis(self, articles: List) -> List[Dict]:
        """
        Processes lista articles z comprehensive AI analysis dla każdego.
        
        Batch processing method - applies NewsAnalyzer do each article
        i returns structured results z analysis data i metadata.
        
        Workflow:
        1. Iterate przez all articles
        2. Apply AI analysis dla każdego article
        3. Combine article data z analysis results
        4. Add processing metadata
        5. Return comprehensive dataset
        
        Wykorzystywana przez:
        - create_intelligent_blog_post() jako first stage
        - Batch analysis commands
        - Research workflows requiring analyzed articles
        - Content curation systems
        
        Args:
            articles: Lista NewsArticle objects do analysis
                     No limit - processes wszystkie provided articles
                     
        Returns:
            List[Dict]: Lista dictionaries, każdy containing:
                       - 'article': Original NewsArticle object
                       - 'analysis': Structured analysis results (dict)
                       - 'processed_at': ISO timestamp
                       
        Error Handling:
            Individual article failures logged ale nie stop batch processing
            Failed articles są skipped, successful ones returned
            
        Data Format:
            Analysis results use Pydantic model_dump() dla serialization
        """
        processed_articles = []
        
        # Process każdy article individually z error isolation
        for article in articles:
            try:
                # Apply AI analysis using NewsAnalyzer
                analysis = self.analyzer.analyze_article(article)
                
                # Create comprehensive result object
                processed_articles.append({
                    "article": article,                          # Original article object
                    "analysis": analysis.model_dump(),          # Pydantic v2 serialization
                    "processed_at": datetime.now().isoformat()  # Processing timestamp
                })
            except Exception as e:
                # Log individual failures ale continue batch processing
                logger.error(f"Error processing article {getattr(article, 'id', 'unknown')}: {e}")
                continue
        
        return processed_articles
    
    def create_intelligent_blog_post(self, topic: str, articles: List) -> Dict:
        """
        Creates comprehensive intelligent blog post combining analysis i generation.
        
        End-to-end workflow combining article analysis z blog generation
        dla sophisticated content creation. Two-stage process: analyze then generate.
        
        Workflow:
        1. Analyze wszystkie articles using NewsAnalyzer
        2. Generate blog post using BlogGenerator
        3. Combine results w comprehensive output
        4. Add metadata dla tracking i quality control
        
        Wykorzystywana przez:
        - NewsOrchestrationService.create_intelligent_blog_summary()
        - High-end content generation workflows
        - Editorial systems requiring AI-powered content
        - API endpoints dla premium blog generation
        
        Args:
            topic: Main topic/theme dla blog post
                  Used by BlogGenerator dla content focus
            articles: Lista NewsArticle objects jako source material
                     All articles analyzed, then used dla generation
                     
        Returns:
            Dict: Comprehensive result containing:
                 - 'blog_post': Generated BlogPostStructure (serialized)
                 - 'analyzed_articles': Full analysis results dla each article
                 - 'metadata': Processing statistics i timestamps
                 - 'error': Error message jeśli processing failed
                 
        Two-Stage Process:
            Stage 1: Article Analysis - structured insights extraction
            Stage 2: Blog Generation - synthesis into blog post
            
        Error Handling:
            Returns error dict on failures instead of raising exceptions
            Comprehensive logging dla debugging
        """
        try:
            # STAGE 1: Comprehensive article analysis
            # Analyze wszystkie articles dla insights i structured data
            analyzed_articles = self.process_articles_with_analysis(articles)
            
            # STAGE 2: Blog post generation
            # Generate blog post using original articles (nie analyzed versions)
            blog_structure = self.blog_generator.generate_blog_post(topic, articles)
            
            # Return comprehensive result combining both stages
            return {
                "blog_post": blog_structure.model_dump(),  # Pydantic v2 serialization
                "analyzed_articles": analyzed_articles,     # Detailed analysis results
                "metadata": {                               # Processing metadata
                    "topic": topic,
                    "articles_processed": len(analyzed_articles),
                    "created_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            # Return error dict instead of raising exception
            logger.error(f"Error creating intelligent blog post: {e}")
            return {"error": str(e)}
    
    def interactive_news_query(self, query: str) -> str:
        """
        Handles interactive natural language queries about news data.
        
        Simple passthrough dla NewsProcessingAgent - provides unified API
        dla interactive capabilities through main orchestrator.
        
        Wykorzystywana przez:
        - Management commands z --interactive flag
        - API endpoints dla conversational news queries
        - Chat interfaces i research tools
        - Development i testing tools
        
        Args:
            query: Natural language question about news data
                  Examples: "Find AI articles", "Show me stats", "Trend analysis"
                  
        Returns:
            str: Agent response using available tools
                Formatted answer based na query complexity
                
        Agent Capabilities:
        - Semantic article search
        - Database statistics
        - Trend analysis
        - Multi-step reasoning
        
        Note:
            Direct delegation do NewsProcessingAgent.process_request()
        """
        # Delegate do NewsProcessingAgent dla interactive capabilities
        return self.agent.process_request(query)