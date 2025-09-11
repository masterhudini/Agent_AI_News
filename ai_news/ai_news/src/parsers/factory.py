import os
import importlib
import inspect
from typing import List, Dict, Type
from .base import BaseScraper
import logging

# Logger dla systemu auto-discovery
logger = logging.getLogger(__name__)


class ScraperFactory:
    """
    Factory Pattern dla zarządzania i tworzenia instancji parserów newsów.
    
    Implementuje automatyczne wykrywanie wszystkich parserów w folderze parsers/ i zapewnia
    jednolity interfejs do ich tworzenia. Jest to główny punkt wejścia dla całego systemu
    scraping'u - umożliwia łatwe dodawanie nowych źródeł bez modyfikacji kodu.
    
    Architektura:
    - Factory Method Pattern: tworzy parsery na podstawie nazwy
    - Registry Pattern: przechowuje mapping name -> class
    - Auto-discovery: automatycznie znajduje nowe parsery
    - Singleton behavior: class-level storage dla performance
    
    Wykorzystywana przez:
    - NewsOrchestrationService do tworzenia parserów
    - Management commands (scrape_news) do listowania źródeł
    - Tests do sprawdzania dostępnych parserów
    - Development tools do reloadowania parserów
    
    Class Variables:
        _scrapers: Dict mapujący nazwy parserów na ich klasy
        _discovered: Flag czy auto-discovery już się wykonało
    """
    
    # Class-level storage - wszystkie instancje współdzielą te dane
    _scrapers: Dict[str, Type[BaseScraper]] = {}
    _discovered = False
    
    @classmethod
    def _discover_scrapers(cls):
        """
        Automatycznie odkrywa wszystkie klasy parserów w folderze parsers/.
        
        Skanuje wszystkie pliki .py w bieżącym folderze, importuje je i szuka klas
        dziedziczących po BaseScraper. Generuje przyjazne nazwy na podstawie nazw klas.
        
        Mechanizm działania:
        1. Skanuje pliki .py (pomija base.py, factory.py, __init__.py)
        2. Importuje każdy moduł używając importlib
        3. Używa inspect.getmembers() do znajdowania klas
        4. Filtruje klasy dziedziczące po BaseScraper
        5. Generuje nazwy: "OpenAIBlogScraper" -> "openai_blog"
        
        Wywoływana przez:
        - create_scraper(): przed tworzeniem parsera
        - get_available_scrapers(): przed zwracaniem listy
        - get_scraper_info(): przed zbieraniem informacji
        
        Note:
            Wykonuje się tylko raz (_discovered flag) dla performance.
            Używa lazy loading - discovery dopiero gdy potrzebne.
        """
        # Avoid redundant discovery - performance optimization
        if cls._discovered:
            return
            
        # Pobieramy path do folderu parsers/
        current_dir = os.path.dirname(__file__)
        
        # Skanujemy wszystkie pliki Python w folderze
        for filename in os.listdir(current_dir):
            # Filtrujemy tylko pliki .py, pomijając utility files
            if filename.endswith('.py') and filename not in ['__init__.py', 'base.py', 'factory.py']:
                module_name = filename[:-3]  # Usuwamy rozszerzenie .py
                
                try:
                    # Dynamic import modułu - relative import z package
                    module = importlib.import_module(f'.{module_name}', package='ai_news.src.parsers')
                    
                    # Przeszukujemy wszystkie obiekty w module looking for scraper classes
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, BaseScraper) and 
                            obj != BaseScraper):  # Exclude base class itself
                            
                            # Name generation: "OpenAIBlogScraper" -> "openai_blog"
                            # Usuwamy suffix "Scraper" i konwertujemy do lowercase
                            scraper_name = name.lower().replace('scraper', '')
                            
                            # Rejestrujemy mapping name -> class
                            cls._scrapers[scraper_name] = obj
                            logger.info(f"Discovered scraper: {scraper_name} -> {name}")
                            
                except Exception as e:
                    # Graceful handling - logged ale nie crashujemy całego discovery
                    logger.error(f"Error importing scraper module {module_name}: {e}")
        
        # Mark discovery as complete i logujemy summary
        cls._discovered = True
        logger.info(f"Auto-discovery complete. Found {len(cls._scrapers)} scrapers.")
    
    @classmethod
    def create_scraper(cls, scraper_type: str) -> BaseScraper:
        """
        Główna factory method - tworzy instancję parsera na podstawie nazwy.
        
        Jest to primary interface dla całego systemu scraping'u. Automatycznie
        trigger'uje discovery jeśli jeszcze się nie wykonało, następnie tworzy
        instancję odpowiedniej klasy parsera.
        
        Wykorzystywana przez:
        - NewsOrchestrationService.scrape_single_source()
        - Management command scrape_news --source
        - Tests do tworzenia specific parserów
        
        Args:
            scraper_type: Nazwa parsera (case-insensitive)
                         np. "openai_blog", "hackernews", "techcrunch_ai"
                         
        Returns:
            BaseScraper: Gotowa instancja parsera do użycia
            
        Raises:
            ValueError: Gdy scraper_type nie został znaleziony
                       Includes lista dostępnych parserów w error message
            
        Example:
            scraper = ScraperFactory.create_scraper("openai_blog")
            articles = scraper.scrape()
        """
        # Ensure discovery happened before attempting to create
        cls._discover_scrapers()
        
        # Case-insensitive lookup
        scraper_class = cls._scrapers.get(scraper_type.lower())
        if not scraper_class:
            # Helpful error message z listą dostępnych options
            available = ', '.join(cls._scrapers.keys())
            raise ValueError(f"Unknown scraper type: {scraper_type}. Available: {available}")
        
        # Tworzymy i zwracamy fresh instance
        return scraper_class()
    
    @classmethod
    def get_available_scrapers(cls) -> List[str]:
        """
        Zwraca listę wszystkich dostępnych nazw parserów.
        
        Używana przez management commands do pokazywania opcji użytkownikowi
        i przez system statystyk do raportowania coverage.
        
        Wykorzystywana przez:
        - scrape_news --list-sources command
        - get_statistics() w NewsOrchestrationService  
        - Tests do weryfikacji discovery
        - Development tools do listowania parserów
        
        Returns:
            List[str]: Lista nazw parserów (bez extensji, lowercase)
                      np. ["openai_blog", "hackernews", "techcrunch_ai"]
                      
        Note:
            Lista jest sorted alphabetically dla consistent output
        """
        # Ensure discovery completed
        cls._discover_scrapers()
        
        # Return sorted list dla consistent output
        return list(cls._scrapers.keys())
    
    @classmethod
    def register_scraper(cls, name: str, scraper_class: Type[BaseScraper]):
        """
        Ręczna rejestracja klasy parsera (alternative to auto-discovery).
        
        Umożliwia dodawanie parserów programmatically, użyteczne dla:
        - Dynamic parsers tworzonych w runtime
        - External plugins
        - Testing z mock parsers
        - Custom parsers nie mieszczących się w auto-discovery pattern
        
        Args:
            name: Nazwa parsera (będzie lowercase)
            scraper_class: Klasa dziedzicząca po BaseScraper
            
        Raises:
            ValueError: Gdy scraper_class nie dziedziczy po BaseScraper
            
        Example:
            class CustomScraper(BaseScraper):
                def scrape(self): return []
            
            ScraperFactory.register_scraper("custom", CustomScraper)
        """
        # Type safety check - zapewniamy consistent interface
        if not issubclass(scraper_class, BaseScraper):
            raise ValueError("Scraper class must inherit from BaseScraper")
        
        # Store w registry z lowercase name dla consistency
        cls._scrapers[name.lower()] = scraper_class
        logger.info(f"Manually registered scraper: {name}")
    
    @classmethod
    def reload_scrapers(cls):
        """
        Force reload wszystkich parserów - użyteczne podczas development.
        
        Czyści registry i ponownie wykonuje auto-discovery. Pozwala na
        hot-reloading nowych parserów bez restartu aplikacji.
        
        Wykorzystywana przez:
        - Development tools
        - Tests wymagające fresh discovery state
        - Management commands z --reload flag
        
        Use cases:
        - Dodano nowy plik parsera
        - Zmieniono nazwę klasy parsera  
        - Debug'owanie discovery issues
        """
        # Clear registry state
        cls._scrapers.clear()
        cls._discovered = False
        
        # Trigger fresh discovery
        cls._discover_scrapers()
    
    @classmethod
    def get_scraper_info(cls) -> Dict[str, str]:
        """
        Zwraca szczegółowe informacje o wszystkich parserach.
        
        Comprehensive metadata o registered parsers, użyteczne dla:
        - System monitoring i health checks
        - Development debugging
        - API endpoints returning scraper info  
        - Admin interfaces
        
        Wykorzystywana przez:
        - Management commands z --info flag
        - REST API endpoints
        - System status pages
        - Development tools
        
        Returns:
            Dict[str, str]: Mapping scraper_name -> metadata dict
                           Każdy scraper ma: class_name, module, source_name
                           
        Example:
            {
                "openai_blog": {
                    "class_name": "OpenAIBlogScraper",
                    "module": "ai_news.src.parsers.openai_blog_scraper", 
                    "source_name": "OpenAI Blog"
                }
            }
        """
        # Ensure discovery completed
        cls._discover_scrapers()
        
        info = {}
        for name, scraper_class in cls._scrapers.items():
            # Collect metadata dla każdego parsera
            info[name] = {
                'class_name': scraper_class.__name__,
                'module': scraper_class.__module__,
                # Instantiate temporarily to get source_name
                # Note: może być expensive dla complex parserów
                'source_name': getattr(scraper_class(), 'source_name', 'Unknown')
            }
        
        return info