# AI News Scraper - Setup Guide

## Wymagania środowiska

### Python 3.12
- Wszystkie biblioteki są kompatybilne z Python 3.12
- Wymagane packages w `requirements.txt`

### Zewnętrzne serwisy
- **OpenAI API** (wymagane): dla embeddings i LLM
- **Qdrant Cloud** (zalecane): dla vector database
- **LangSmith** (opcjonalne): dla monitorowania LangChain

## Krok 1: Instalacja i konfiguracja w PyCharm

### 1.1 Konfiguracja środowiska Python
```bash
# Stwórz virtual environment
python -m venv venv

# Aktywuj (Windows)
venv\Scripts\activate

# Zainstaluj zależności
pip install -r requirements.txt
```

### 1.2 Konfiguracja zmiennych środowiskowych
Skopiuj `.env.example` do `.env` w root projektu:

```bash
# Environment configuration
ENVIRONMENT=development

# OpenAI Configuration (WYMAGANE)
OPENAI_API_KEY=sk-twoj_openai_api_key_tutaj

# Qdrant Cloud Configuration (ZALECANE)
QDRANT_URL=https://32ef913e-7184-44e8-89c4-a3ebb467505f.europe-west3-0.gcp.cloud.qdrant.io
QDRANT_API_KEY=twoj_qdrant_api_key_tutaj
QDRANT_COLLECTION_NAME=news_articles

# LangChain Configuration (OPCJONALNE)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=twoj_langsmith_api_key
LANGCHAIN_PROJECT=ai-news-scraper

# Model Configuration (używa defaults jeśli nie ustawione)
DEFAULT_LLM_MODEL=gpt-4o-mini
DEFAULT_EMBEDDING_MODEL=text-embedding-3-small
DEFAULT_TEMPERATURE=0.7
```

### 1.3 Konfiguracja PyCharm

1. **Interpreter Python**: Ustaw na `venv/Scripts/python.exe`

2. **Working Directory**: Ustaw na folder `ai_news` (tam gdzie jest `manage.py`)
   ```
   C:\Users\Hudini\PythonProjects\Agent_AI_News\ai_news
   ```

3. **Environment Variables** w Run Configuration:
   - Dodaj wszystkie zmienne z `.env` lub
   - PyCharm automatycznie załaduje `.env` dzięki `settings.py`

## Krok 2: Inicjalizacja Django

### 2.1 Migracje bazy danych
```bash
# Przejdź do folderu z manage.py
cd ai_news

# Stwórz migracje
python manage.py makemigrations

# Wykonaj migracje  
python manage.py migrate
```

### 2.2 Test konfiguracji
```bash
# Sprawdź czy Django działa
python manage.py check

# Test ładowania konfiguracji
python manage.py shell
>>> from ai_news.core.config import get_app_config
>>> config = get_app_config()
>>> print(config.openai_api_key)  # Powinno pokazać twój API key
```

## Krok 3: Uruchomienie aplikacji

### 3.1 Serwer Django (w PyCharm)

**Run Configuration:**
- Script path: `C:\Users\Hudini\PythonProjects\Agent_AI_News\ai_news\manage.py`  
- Parameters: `runserver`
- Working directory: `C:\Users\Hudini\PythonProjects\Agent_AI_News\ai_news`
- Environment variables: automatycznie z `.env`

**Lub z terminala:**
```bash
cd ai_news
python manage.py runserver
```

### 3.2 Test scraperów
```bash
# Lista dostępnych scraperów
python manage.py scrape_news --list-sources

# Test single source
python manage.py scrape_news --source openai_blog

# Pełny pipeline
python manage.py scrape_news --all --generate-summary
```

## Krok 4: Pipeline Runner - główny interfejs

### 4.1 Uruchomienie z kodu Python
```python
# W PyCharm console lub nowym script
from ai_news.src.pipeline_runner import run_full_news_pipeline

# Pełny pipeline
results = run_full_news_pipeline(generate_summary=True)
print(results)
```

### 4.2 Uruchomienie bezpośrednie
```bash
cd ai_news
python -m ai_news.src.pipeline_runner
```

### 4.3 PyCharm Run Configuration dla Pipeline
**Script path:** `C:\Users\Hudini\PythonProjects\Agent_AI_News\ai_news\ai_news\src\pipeline_runner.py`
**Working directory:** `C:\Users\Hudini\PythonProjects\Agent_AI_News\ai_news`

## Krok 5: Dostępne komendy

### Management Commands
```bash
# Scraping
python manage.py scrape_news --all                    # Wszystkie źródła  
python manage.py scrape_news --source openai_blog     # Jedno źródło
python manage.py scrape_news --all --generate-summary # Z AI summary

# Lista źródeł
python manage.py scrape_news --list-sources
```

### Pipeline Runner Functions
```python
from ai_news.src.pipeline_runner import (
    run_full_news_pipeline,     # Pełny pipeline
    scrape_single_source,       # Jedno źródło
    generate_daily_summary,     # Podsumowanie  
    get_system_stats,           # Statystyki
    query_news_database         # AI queries
)

# Przykłady użycia
results = run_full_news_pipeline()
stats = get_system_stats()
answer = query_news_database("What are the latest AI trends?")
```

## Krok 6: Troubleshooting

### Typowe problemy

1. **Brak .env**: Skopiuj `.env.example` do `.env` i wypełnij API keys

2. **Working Directory**: Upewnij się że PyCharm ma working directory na `ai_news` folder

3. **Import errors**: Sprawdź czy path w PyCharm jest poprawny i interpreter używa virtual env

4. **Qdrant connection**: Sprawdź czy `QDRANT_URL` i `QDRANT_API_KEY` są poprawne

5. **OpenAI errors**: Sprawdź czy `OPENAI_API_KEY` jest poprawny i ma credits

### Debug w PyCharm

1. Ustaw breakpoints w `pipeline_runner.py`
2. Debug z konfiguracją dla `pipeline_runner.py`  
3. Sprawdź wartości zmiennych środowiskowych w debugger

### Logs
- Console output dla podstawowych informacji
- `news_scraper.log` dla szczegółowych logów
- Django admin dla przeglądania artykułów

## Podsumowanie

Po wykonaniu setup:

1. **Django server**: `python manage.py runserver`
2. **Pipeline**: `python -m ai_news.src.pipeline_runner` lub w PyCharm
3. **Management**: `python manage.py scrape_news --all`
4. **AI Queries**: używaj `pipeline_runner` functions

Aplikacja automatycznie:
- Ładuje konfigurację z `.env`
- Łączy się z Qdrant Cloud
- Konfiguruje dependency injection
- Zapewnia error handling i logging