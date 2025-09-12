from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
import requests
import logging

# Logger do zapisywania informacji o działaniu parserów
logger = logging.getLogger(__name__)


class NewsArticleData:
    """
    Klasa danych reprezentująca pojedynczy artykuł newsowy.
    
    Jest to główna struktura danych używana przez wszystkie parsery do przechowywania 
    informacji o artykułach. Stanowi standardowy interfejs między parserami a resztą systemu.
    
    Wykorzystywana przez:
    - Wszystkie parsery do zwracania wyników scraping'u
    - System deduplikacji do porównywania artykułów
    - Serwis podsumowań do generowania blogów
    - Django ORM do zapisywania w bazie danych (NewsArticle model)
    
    Attributes:
        title (str): Tytuł artykułu - główny identyfikator treści
        content (str): Pełna treść artykułu lub streszczenie
        url (str): Unikalny URL artykułu - używany do wykrywania duplikatów
        source (str): Nazwa źródła (np. "OpenAI Blog", "TechCrunch AI")
        published_date (datetime): Data publikacji - używana do sortowania i filtrowania
        author (str, optional): Autor artykułu jeśli dostępny
    """
    
    def __init__(self, title: str, content: str, url: str, source: str, 
                 published_date: datetime, author: Optional[str] = None):
        """
        Inicjalizuje obiekt artykułu z wymaganymi danymi.
        
        Args:
            title: Tytuł artykułu (wymagany, używany w deduplication)
            content: Treść artykułu (wymagana, używana w semantic similarity)
            url: Unikalny URL (wymagany, pierwotne wykrywanie duplikatów)
            source: Nazwa źródła (wymagane, grupowanie i statystyki)
            published_date: Data publikacji (wymagana, sortowanie chronologiczne)
            author: Autor artykułu (opcjonalne, metadata)
        """
        self.title = title
        self.content = content
        self.url = url
        self.source = source
        self.published_date = published_date
        self.author = author


class BaseScraper(ABC):
    """
    Abstrakcyjna klasa bazowa dla wszystkich parserów newsów.
    
    Implementuje wspólną funkcjonalność dla wszystkich typów parserów (RSS, API, web scraping).
    Zapewnia jednolitego interfejsu dla Factory Pattern i zarządzania sesjami HTTP.
    
    Architektura:
    - Template Method Pattern: definiuje szkielet działania parsera
    - Strategy Pattern: każda implementacja ma swoją strategię scrapingu
    - Session Management: zarządza połączeniami HTTP z nagłówkami
    
    Wykorzystywana przez:
    - ScraperFactory do tworzenia instancji parserów
    - RSSFeedScraper jako klasa bazowa dla RSS feedów
    - Specific scrapers (HackerNews, Reddit) jako bezpośrednia baza
    - NewsOrchestrationService do wykonywania scraping'u
    
    Implementacje muszą zdefiniować:
    - scrape(): główna metoda pobierająca dane ze źródła
    """
    
    def __init__(self, source_name: str):
        """
        Inicjalizuje parser z nazwą źródła i konfiguracją HTTP.
        
        Tworzy sesję requests z nagłówkami imitującymi przeglądarkę web,
        co zmniejsza prawdopodobieństwo blokowania przez anti-bot systemy.
        
        Args:
            source_name: Czytelna nazwa źródła (np. "OpenAI Blog")
                        Używana w NewsArticleData.source i logach
        """
        self.source_name = source_name
        
        # Tworzymy sesję HTTP z persistent connection pooling
        self.session = requests.Session()
        
        # Ustawiamy User-Agent żeby wyglądać jak prawdziwa przeglądarka
        # Chroni przed blokowaniem przez systemy anti-bot
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    @abstractmethod
    def scrape(self) -> List[NewsArticleData]:
        """
        Główna metoda scraping'u - musi być zaimplementowana przez każdy parser.
        
        Jest to serce Template Method Pattern - definiuje kontrakt dla wszystkich parserów.
        Każda implementacja używa swojej strategii (RSS, API, web scraping).
        
        Returns:
            List[NewsArticleData]: Lista znalezionych artykułów
                                 Może być pusta jeśli źródło nie ma nowych treści
                                 
        Raises:
            Exception: Implementacje powinny gracefully handle błędy
                      i zwracać pustą listę zamiast crashować
        """
        pass
    
    def _clean_text(self, text: str) -> str:
        """
        Czyści i normalizuje tekst z różnych źródeł.
        
        Unified text processing dla wszystkich parserów - usuwa nadmiarowe whitespace,
        łamań linii i inne artefakty pochodzące z HTML, RSS lub API responses.
        
        Wykorzystywana przez:
        - RSS parsery do czyszczenia treści z feedów
        - API parsery do normalizacji JSON responses
        - Specific parsers do custom text processing
        
        Args:
            text: Surowy tekst do wyczyszczenia (może być None/empty)
            
        Returns:
            str: Wyczyszczony tekst lub pusty string dla invalid input
            
        Example:
            "  Multiple   spaces\\n\\n  text  " -> "Multiple spaces text"
        """
        if not text:
            return ""
        
        # Używamy split() bez argumentów - to automatycznie usuwa wszystkie whitespace
        # i łączy je pojedynczymi spacjami
        return ' '.join(text.split())
    
    def _parse_date(self, date_str: str) -> datetime:
        """
        Parsuje string daty do obiektu datetime z intelligent fallback.
        
        Obsługuje różne formaty dat występujące w RSS feedach i API:
        - ISO format z 'Z' (UTC): "2023-12-01T10:30:00Z"  
        - ISO format bez timezone: "2023-12-01T10:30:00"
        - RFC 2822 format (RSS): "Tue, 26 Aug 2024 15:21:19 +0000"
        - Inne formaty: fallback do current time
        
        Wykorzystywana przez:
        - RSS parsery dla <published> i <updated> tagów
        - API parsery dla timestamp fields
        - Date normalization w całym systemie
        
        Args:
            date_str: String reprezentujący datę (może być None/empty)
            
        Returns:
            datetime: Sparsowana data lub datetime.now() jako fallback
            
        Note:
            Używa datetime.now() zamiast crashowania - lepsze dla production stability
        """
        if not date_str:
            return datetime.now()
            
        try:
            # RFC 3339 format z Z oznacza UTC timezone
            if date_str.endswith('Z'):
                # Zamieniamy 'Z' na '+00:00' bo fromisoformat() wymaga explicit offset
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                
            # Próbujemy standardowy ISO format bez timezone
            return datetime.fromisoformat(date_str)
            
        except (ValueError, AttributeError):
            # Próbujemy RFC 2822 format (używany w RSS feeds)
            try:
                from email.utils import parsedate_to_datetime
                return parsedate_to_datetime(date_str)
            except (ValueError, TypeError):
                # Logujemy warning ale nie crashujemy - production stability
                logger.warning(f"Could not parse date: {date_str}")
                
                # Fallback do current time - artykuł będzie traktowany jako "fresh"
                return datetime.now()