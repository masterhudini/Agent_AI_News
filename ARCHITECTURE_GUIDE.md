# 🏗️ AI News Scraper - Architecture Guide

## Przewodnik programisty po aplikacji

Ten dokument zawiera szczegółową dokumentację architektury systemu AI News Scraper. 
Każdy komponent jest opisany z perspektywy jego roli w całym systemie.

---

## 📋 Spis treści

1. [Architektura ogólna](#architektura-ogólna)
2. [System parserów](#system-parserów)
3. [Deduplication Engine](#deduplication-engine) 
4. [LangChain Integration](#langchain-integration)
5. [News Orchestration Service](#news-orchestration-service)
6. [Management Commands](#management-commands)

---

## 🎯 Architektura ogólna

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │────│    Parsers       │────│  Deduplication  │
│  (RSS/API/Web)  │    │   (34 scrapers)  │    │   (Hash + AI)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  News Database  │◄───│ News Orchestrator│◄───│  LangChain AI   │
│   (Django ORM)  │    │    (Service)     │    │  (Analysis)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Blog Summaries  │◄───│ Summarization    │◄───│   Vector DB     │
│   (Generated)   │    │   (AI-powered)   │    │   (Qdrant)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

---

## 🔧 System parserów

### Struktura folderów
```
src/parsers/
├── base.py              # Klasy bazowe i struktury danych
├── factory.py           # Auto-discovery i Factory Pattern  
├── rss_base.py          # Bazowy scraper dla RSS
├── openai_blog_scraper.py    # Parser dla OpenAI Blog
├── hackernews_scraper.py     # Parser dla Hacker News API
├── ... (32+ więcej parserów)
```

### Kluczowe klasy:

#### `NewsArticleData` (base.py)
Główna struktura danych reprezentująca artykuł newsowy.

**Rola:** Standardowy interfejs między wszystkimi komponentami systemu.
**Wykorzystanie:** Parsery → Deduplication → Database → Summarization

#### `BaseScraper` (base.py) 
Abstrakcyjna klasa bazowa implementująca Template Method Pattern.

**Rola:** Zapewnia wspólną funkcjonalność (HTTP session, date parsing, text cleaning)
**Implementacje:** RSSFeedScraper, HackerNewsScraper, Reddit scrapers

#### `ScraperFactory` (factory.py)
Auto-discovery system z Factory Pattern.

**Mechanizm:**
1. Skanuje folder `parsers/` szukając plików `*_scraper.py`
2. Importuje dynamicznie każdy moduł
3. Znajduje klasy dziedziczące po `BaseScraper`
4. Generuje user-friendly nazwy: `"OpenAIBlogScraper"` → `"openai_blog"`
5. Przechowuje w registry: `Dict[str, Type[BaseScraper]]`

---

## 🔍 Deduplication Engine

### Dwa poziomy deduplikacji:

#### 1. **ContentHashDeduplicator** - Exact matches
```python
# SHA256 hash z pełnej treści artykułu
content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

# Check w database
if NewsArticle.objects.filter(content_hash=content_hash).exists():
    return True  # Exact duplicate
```

#### 2. **VectorDeduplicator** - Semantic similarity
```python  
# OpenAI embeddings (1536-dimensional vectors)
embedding = openai.embeddings.create(input=content, model="text-embedding-3-small")

# Qdrant vector search z 85% threshold
similar = qdrant_client.search(
    collection_name="news_articles",
    query_vector=embedding,
    limit=1,
    score_threshold=0.85
)
```

#### `DuplicationService` - Orchestrator
Łączy oba approaches:
1. **Fast path:** Exact hash matching (najszybsze)
2. **Smart path:** Semantic similarity (AI-powered)
3. **Storage:** Dodaje unique articles do vector index

---

## 🤖 LangChain Integration

### Komponenty AI w systemie:

#### `NewsAnalyzer` (langchain_chains.py)
**Cel:** Strukturalna analiza artykułów z AI
**Input:** NewsArticleData  
**Output:** Structured Pydantic models z kategoriami, importance scores, key topics

```python
# LCEL chain pattern
analysis_chain = analysis_prompt | llm | output_parser

# Structured output
class NewsAnalysisResult(BaseModel):
    key_topics: List[str]
    importance_score: float  # 0.0-1.0
    category: str           # "AI", "Tech", "Business"
    summary: str
```

#### `BlogGenerator` (langchain_chains.py)
**Cel:** Generowanie blog posts z multiple articles
**Mechanizm:** Map-reduce pattern dla dużych zbiorów artykułów

#### `NewsProcessingAgent` (langchain_chains.py)  
**Cel:** Conversational AI agent z tools
**Tools:** Search articles, get stats, analyze trends
**Architecture:** OpenAI Functions + LangChain agents

---

## 🎼 News Orchestration Service

### `NewsOrchestrationService` (news_service.py)

Jest to główny koordinator całego systemu. Łączy wszystkie komponenty:

```python
class NewsOrchestrationService:
    def __init__(self):
        self.duplication_service = DuplicationService()      # Deduplication
        self.blog_summary_service = BlogSummaryService()     # AI Summarization  
        self.langchain_orchestrator = LangChainOrchestrator() # AI Analysis
```

#### Główne workflow:

1. **`scrape_all_sources()`** - Orchestrates scraping z wszystkich parserów
2. **`scrape_single_source()`** - Single source z deduplication
3. **`run_full_pipeline()`** - Complete end-to-end process
4. **`create_intelligent_blog_summary()`** - AI-powered blog generation

#### Pipeline flow:
```
Sources → Scrapers → Raw Articles → Deduplication → Unique Articles → Database
                                      ↓
Blog Summaries ← AI Summarization ← LangChain Analysis ← Vector Index
```

---

## 💻 Management Commands  

### `scrape_news` command
**Location:** `management/commands/scrape_news.py`

**Usage:**
```bash
python manage.py scrape_news --all                    # Scrape wszystko
python manage.py scrape_news --source openai_blog     # Specific source
python manage.py scrape_news --list-sources           # List all parsers
python manage.py scrape_news --all --generate-summary # Z AI summary
```

### `langchain_analysis` command  
**Location:** `management/commands/langchain_analysis.py`

**Usage:**
```bash
python manage.py langchain_analysis --query "What are the latest AI trends?"
python manage.py langchain_analysis --search "machine learning" --limit 5
python manage.py langchain_analysis --analyze --topic "AI News" 
python manage.py langchain_analysis --intelligent-summary --topic "Tech"
```

---

## 🔄 Data Flow Diagram

```
┌─ RSS Feeds ─┐  ┌─ API Sources ─┐  ┌─ Web Scraping ─┐
│   34 feeds  │  │  Hacker News  │  │   Reddit etc   │
└─────────────┘  └───────────────┘  └────────────────┘
       │                 │                   │
       └─────────────────┼───────────────────┘
                         ▼
              ┌──────────────────┐
              │  ScraperFactory  │ ◄── Auto-discovery
              │   (34 parsers)   │
              └──────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │ NewsArticleData  │ ◄── Standardized format
              │   (title, url,   │
              │  content, date)  │
              └──────────────────┘
                         │
                         ▼
          ┌─────────────────────────┐
          │  DuplicationService     │
          │ ┌─────────┐ ┌─────────┐ │
          │ │SHA256   │ │Vector   │ │ ◄── Dual deduplication
          │ │Hash     │ │Search   │ │
          │ └─────────┘ └─────────┘ │
          └─────────────────────────┘
                         │
                    ┌────┴────┐
                    ▼         ▼
          ┌─────────────┐   ┌──────────────┐
          │ NewsArticle │   │ Vector Index │
          │ (Database)  │   │  (Qdrant)    │
          └─────────────┘   └──────────────┘
                    │               │
                    └───────┬───────┘
                            ▼
              ┌──────────────────────┐
              │ LangChain Analysis   │ ◄── AI processing
              │ - Topic extraction   │
              │ - Importance scoring │  
              │ - Summarization     │
              └──────────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │   Blog Summary   │ ◄── Generated content
              │  (AI-powered)    │
              └──────────────────┘
```

---

## 🧪 Testing Architecture

### Test Structure (mirrors src/):
```
tests/
├── base.py                 # Test utilities i mocks
├── parsers/
│   ├── test_base.py        # BaseScraper tests
│   ├── test_factory.py     # Auto-discovery tests
│   └── test_specific_scrapers.py
├── test_deduplication.py   # Hash + Vector tests
├── test_langchain_chains.py # AI components tests
├── test_news_service.py    # Orchestration tests
└── management/commands/    # Command tests
```

### Kluczowe wzorce testowe:
- **Comprehensive mocking:** OpenAI API, Qdrant, RSS feeds
- **Factory testing:** Auto-discovery i error handling
- **Integration tests:** End-to-end pipeline testing
- **Command testing:** CLI interface testing

---

## 🚀 Deployment Considerations

### Required Services:
1. **Qdrant Vector Database** - Port 6333
2. **OpenAI API Access** - API key required
3. **Django Database** - SQLite/PostgreSQL
4. **Python 3.12+** - Latest optimizations

### Environment Variables:
```bash
OPENAI_API_KEY=your-key-here          # Required
LANGCHAIN_API_KEY=langsmith-key       # Optional (monitoring)
QDRANT_HOST=localhost                 # Vector DB
QDRANT_PORT=6333                      # Vector DB port
```

### Scaling Points:
- **Parser count:** Auto-discovery scales to 100+ sources
- **Vector similarity:** Qdrant handles millions of articles  
- **AI processing:** Rate-limited by OpenAI quotas
- **Database:** Standard Django ORM scaling patterns

---

*Ten przewodnik zawiera kluczowe informacje architektury. Szczegółowe docstringi w kodzie zawierają implementation details dla każdego komponentu.*