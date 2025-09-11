# AI News Scraper with LangChain (Python 3.12)

A state-of-the-art Django application for intelligent news aggregation, featuring advanced AI-powered content analysis and blog generation. Built exclusively with LangChain, OpenAI, and modern Python 3.12 patterns.

## 🌟 Key Features

### **🏗️ Architecture**
- **Modular Scraper Design**: Extensible Factory pattern for easy source integration
- **Modern Python 3.12**: Leveraging latest language optimizations and type hints
- **LangChain-First**: No fallbacks - pure LangChain implementation throughout
- **Production Ready**: Comprehensive logging, error handling, and monitoring

### **📡 Data Sources**
- **TechCrunch** - Latest tech industry news
- **Ars Technica** - In-depth technology coverage  
- **The Verge** - Consumer technology and culture
- **Hacker News** - Developer and startup community insights
- **Extensible**: Easy to add new RSS feeds and API sources

### **🧠 AI-Powered Intelligence**
- **Advanced Deduplication**:
  - SHA256 content hashing for exact matches
  - OpenAI embeddings + Qdrant for semantic similarity (85% threshold)
  - Prevents content redundancy across sources
  
- **Intelligent Analysis**:
  - Topic extraction and categorization
  - Importance scoring (0.0-1.0)
  - Sentiment analysis capabilities
  - Structured output with Pydantic v2

- **Smart Summarization**:
  - Map-reduce processing for large document sets
  - Context-aware blog post generation
  - Professional tone with actionable insights
  - 400-600 word summaries optimized for readability

### **🤖 Interactive AI Agent**
- **OpenAI Functions**: Latest agent architecture
- **Natural Language Queries**: "What are the latest AI trends?"
- **Real-time Analysis**: Live database insights and statistics
- **Tool Integration**: Search, analyze, and report capabilities

### **⚡ Technical Excellence**
- **Modern LangChain**: LCEL chains, structured output, function calling
- **Vector Search**: Qdrant integration for semantic similarity
- **Type Safety**: Full Python 3.12 type hints throughout
- **Async Ready**: Optimized for concurrent operations
- **Docker Support**: Easy deployment and scaling

## 📋 Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.12+ | Core runtime with latest optimizations |
| **OpenAI API Key** | Required | GPT-4 and embeddings (no fallbacks) |
| **Qdrant** | 1.11.1+ | Vector database for semantic search |
| **Django** | 5.0.8+ | Web framework and ORM |

## 🚀 Quick Start

### 1. **Environment Setup**
```bash
# Clone and navigate
git clone <repository-url>
cd Agent_AI_News

# Create virtual environment (Python 3.12)
python3.12 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. **Configuration**
Create `.env` file or set environment variables:
```bash
# Required
OPENAI_API_KEY=your-openai-api-key-here

# Optional (for monitoring)
LANGCHAIN_API_KEY=your-langsmith-key-here
LANGCHAIN_PROJECT=ai-news-scraper
```

### 3. **Infrastructure Setup**
```bash
# Start Qdrant vector database
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant

# Or using docker-compose (create docker-compose.yml):
# version: '3.8'
# services:
#   qdrant:
#     image: qdrant/qdrant
#     ports:
#       - "6333:6333"
#     volumes:
#       - ./qdrant_data:/qdrant/storage
```

### 4. **Django Application**
```bash
cd ai_news

# Database setup
python manage.py makemigrations
python manage.py migrate

# Create admin user (optional)
python manage.py createsuperuser

# Test installation
python manage.py check
```

## 🎯 Usage Guide

### **📊 News Scraping & Management**

| Command | Description | Example |
|---------|-------------|---------|
| **List Sources** | Show available scrapers | `python manage.py scrape_news --list-sources` |
| **Scrape All** | Gather from all sources | `python manage.py scrape_news --all` |
| **Specific Source** | Target single source | `python manage.py scrape_news --source techcrunch` |
| **With Summary** | Scrape + generate blog | `python manage.py scrape_news --all --generate-summary` |

### **🤖 AI-Powered Analysis**

#### **Interactive Querying**
```bash
# Natural language questions about your news data
python manage.py langchain_analysis --query "What are the latest AI trends?"
python manage.py langchain_analysis --query "Show me articles about GPT-4"
python manage.py langchain_analysis --query "What's trending in cybersecurity?"
```

#### **Content Discovery**
```bash
# Semantic search across all articles
python manage.py langchain_analysis --search "machine learning"
python manage.py langchain_analysis --search "cryptocurrency regulation"
python manage.py langchain_analysis --search "quantum computing breakthrough"
```

#### **Deep Analysis**
```bash
# Analyze articles with AI insights
python manage.py langchain_analysis --analyze --topic "AI News" --limit 10
python manage.py langchain_analysis --analyze --topic "Blockchain" --model gpt-4o-mini
```

#### **Blog Generation**
```bash
# Create intelligent blog summaries
python manage.py langchain_analysis --intelligent-summary --topic "Tech News"
python manage.py generate_summary --type weekly --topic "AI Developments"
```

### **📈 Monitoring & Maintenance**

```bash
# View comprehensive statistics
python manage.py news_stats

# Database cleanup (remove old articles)
python manage.py news_stats --cleanup --cleanup-days 30

# Check system health
python manage.py check --deploy
```

### **🌐 Web Interface**

```bash
# Start development server
python manage.py runserver

# Access admin interface
# http://localhost:8000/admin/

# API endpoints available for integration
```

## Architecture

### Components

1. **Scrapers (`scrapers.py`)**:
   - `BaseScraper`: Abstract base class
   - `RSSFeedScraper`: Generic RSS scraper
   - `HackerNewsScraper`: API-based scraper for Hacker News
   - `ScraperFactory`: Factory for creating scrapers

2. **Models (`models.py`)**:
   - `NewsArticle`: Stores scraped articles
   - `BlogSummary`: Stores generated summaries

3. **Deduplication (`deduplication.py`)**:
   - `VectorDeduplicator`: Semantic similarity using Qdrant
   - `ContentHashDeduplicator`: Exact content matching
   - `DuplicationService`: Orchestrates deduplication

4. **Summarization (`summarization.py`)**:
   - `OpenAISummarizer`: Uses OpenAI GPT for summaries
   - `HuggingFaceSummarizer`: Uses local transformers models
   - `BlogSummaryService`: Manages summary generation

5. **Orchestration (`news_service.py`)**:
   - `NewsOrchestrationService`: Main service coordinating all operations
   - LangChain integration for intelligent processing

6. **LangChain Chains (`langchain_chains.py`)**:
   - `LangChainNewsAnalyzer`: Article analysis with structured output
   - `LangChainBlogGenerator`: Intelligent blog post generation
   - `NewsProcessingAgent`: Conversational AI agent for queries
   - `LangChainNewsOrchestrator`: Main LangChain orchestrator

### Adding New Scrapers

1. Create a new scraper class inheriting from `BaseScraper`
2. Implement the `scrape()` method
3. Register with `ScraperFactory`:

```python
class MyNewsScraper(BaseScraper):
    def scrape(self) -> List[NewsArticleData]:
        # Implementation here
        pass

# Register the scraper
ScraperFactory.register_scraper('mynews', MyNewsScraper)
```

## Configuration

### Settings (`settings.py`)

- `QDRANT_HOST`: Qdrant server host (default: 'localhost')
- `QDRANT_PORT`: Qdrant server port (default: 6333)
- `OPENAI_API_KEY`: OpenAI API key for better summaries (optional)

#### LangChain Configuration
- `LANGCHAIN_TRACING_V2`: Enable LangSmith tracing (default: True)
- `LANGCHAIN_API_KEY`: LangSmith API key (optional)
- `LANGCHAIN_PROJECT`: Project name for LangSmith tracking
- `LANGCHAIN_DEFAULT_MODEL`: Default OpenAI model (default: 'gpt-3.5-turbo')
- `LANGCHAIN_EMBEDDING_MODEL`: Embedding type ('openai' or 'huggingface')
- `LANGCHAIN_TEMPERATURE`: Default temperature for LLM calls
- `LANGCHAIN_MAX_TOKENS`: Default max tokens

### Environment Variables

You can set these as environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `LANGCHAIN_API_KEY`: Your LangSmith API key (optional)
- `HUGGINGFACE_API_KEY`: Your HuggingFace API key (optional)

## API Usage

### Programmatic Usage

```python
from ai_news.src.news_service import NewsOrchestrationService

# Initialize service with LangChain
service = NewsOrchestrationService(use_langchain=True, embedding_type="openai")

# Run full pipeline
results = service.run_full_pipeline(generate_summary=True)

# Create intelligent blog summary
intelligent_summary = service.create_intelligent_blog_summary("AI News")

# Search similar articles
similar_articles = service.search_similar_articles("machine learning", limit=5)

# Interactive query
response = service.interactive_news_query("What are the latest AI trends?")

# Analyze articles with LangChain
articles = service.get_latest_articles(limit=10)
analyzed = service.analyze_articles_with_langchain(articles)

# Get statistics
stats = service.get_statistics()
```

### LangChain Components Usage

```python
from ai_news.src.langchain_chains import (
    LangChainNewsAnalyzer,
    LangChainBlogGenerator, 
    NewsProcessingAgent,
    LangChainNewsOrchestrator
)

# Analyze individual articles
analyzer = LangChainNewsAnalyzer(model_type="openai")
analysis = analyzer.analyze_article(article)

# Generate structured blog posts
blog_generator = LangChainBlogGenerator(model_type="openai")
blog_post = blog_generator.generate_blog_post("AI News", articles)

# Use conversational agent
agent = NewsProcessingAgent()
response = agent.process_request("Show me articles about GPT-4")

# Full orchestration
orchestrator = LangChainNewsOrchestrator()
result = orchestrator.create_intelligent_blog_post("AI News", articles)
```

## Contributing

1. Add new scrapers in `scrapers.py`
2. Register them with `ScraperFactory`
3. Update tests and documentation
4. Follow existing code patterns

## Dependencies

### Core Dependencies
- Django 5.2.6
- requests, beautifulsoup4, feedparser (scraping)
- sentence-transformers, qdrant-client (deduplication)
- transformers, openai (summarization)

### LangChain Dependencies
- langchain, langchain-core (core framework)
- langchain-openai (OpenAI integration)
- langchain-community (community integrations)
- langsmith (observability and tracing)
- faiss-cpu (vector search)
- tiktoken (tokenization)
- pydantic (structured output)

## License

MIT License