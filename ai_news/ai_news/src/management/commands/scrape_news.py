# Django management command framework
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

# Core application services
from ai_news.src.news_service import NewsOrchestrationService  # Main orchestration service
from ai_news.src.parsers import ScraperFactory                 # Auto-discovery scraper management


class Command(BaseCommand):
    """
    Django management command dla comprehensive news scraping operations.
    
    Główny command-line interface dla scraping news articles z multiple sources.
    Supports single source scraping, batch processing wszystkich sources,
    AI-powered summary generation, i source management operations.
    
    Architektura:
    - Django BaseCommand: Standardowy Django CLI framework
    - NewsOrchestrationService integration: Unified API dla scraping operations
    - ScraperFactory integration: Auto-discovery i source management
    - Flexible argument parsing: Multiple operation modes
    
    Available Operations:
    - Single source scraping: --source <name>
    - Batch scraping wszystkich sources: --all
    - AI summary generation: --generate-summary
    - Source listing: --list-sources
    - Statistics reporting: automatic after operations
    
    Wykorzystywana przez:
    - Scheduled cron jobs dla automated scraping
    - Manual operations dla specific source updates
    - Development i testing workflows
    - System administration i maintenance
    
    Example Usage:
    python manage.py scrape_news --all --generate-summary
    python manage.py scrape_news --source openai_blog
    python manage.py scrape_news --list-sources
    
    Features:
    - Comprehensive error handling i reporting
    - Detailed progress output i statistics
    - Flexible operation modes dla different use cases
    - Integration z AI summarization capabilities
    """
    
    help = 'Scrape news articles from various sources'

    def add_arguments(self, parser):
        """
        Defines command-line arguments dla scrape_news management command.
        
        Konfiguruje comprehensive argument parser supporting multiple operation modes.
        Each argument enables different scraping workflows i functionality.
        
        Arguments Defined:
        --source: Target specific news source dla focused scraping
        --all: Process wszystkie available sources w batch operation
        --generate-summary: Enable AI-powered blog summary generation
        --list-sources: Display wszystkie registered scrapers
        
        Argument Design:
        - Mutually exclusive primary operations (source vs all vs list)
        - Optional AI enhancement (generate-summary)
        - Clear help text dla user guidance
        - Type safety i validation
        
        Args:
            parser: Django ArgumentParser instance dla argument configuration
        """
        # Primary operation: target specific source
        parser.add_argument(
            '--source',
            type=str,
            help='Specific source to scrape (e.g., openai_blog, hackernews, techcrunch_ai)',
        )
        
        # Primary operation: batch process wszystkie sources
        parser.add_argument(
            '--all',
            action='store_true',
            help='Scrape from all available sources (comprehensive batch operation)',
        )
        
        # Enhancement option: AI-powered content generation
        parser.add_argument(
            '--generate-summary',
            action='store_true',
            help='Generate AI-powered blog summaries after scraping (daily + weekly)',
        )
        
        # Utility operation: source discovery i management
        parser.add_argument(
            '--list-sources',
            action='store_true',
            help='List all available scrapers from auto-discovery system',
        )

    def handle(self, *args, **options):
        """
        Main command execution logic handling all scraping operations.
        
        Orchestrates different operation modes based na command-line arguments.
        Provides comprehensive workflow dla news scraping z error handling,
        progress reporting, i optional AI summarization.
        
        Operation Modes:
        1. List Sources: Display available scrapers i exit
        2. Single Source: Target specific source dla focused scraping
        3. Batch All: Process wszystkie sources w comprehensive operation
        4. Summary Generation: Optional AI-powered content creation
        5. Statistics: Always display final system state
        
        Error Handling:
        - CommandError dla user-facing errors
        - Detailed error messages dla troubleshooting
        - Graceful degradation dla partial failures
        - Comprehensive logging i reporting
        
        Args:
            *args: Positional arguments (unused)
            **options: Parsed command-line arguments dict
            
        Raises:
            CommandError: User-facing errors dla invalid arguments lub critical failures
            
        Output:
        - Success messages dla completed operations
        - Detailed statistics i progress reporting
        - Error messages dla troubleshooting
        - Summary information dla generated content
        """
        # Initialize NewsOrchestrationService z default configuration
        # Provides unified API dla wszystkich scraping i AI operations
        service = NewsOrchestrationService()
        
        # OPERATION MODE 1: List Available Sources
        if options['list_sources']:
            # Query auto-discovery system dla registered scrapers
            sources = ScraperFactory.get_available_scrapers()
            self.stdout.write(
                self.style.SUCCESS(f"Available scrapers ({len(sources)}): {', '.join(sources)}")
            )
            return  # Exit after listing - no further operations

        # OPERATION MODE 2: Single Source Scraping
        if options['source']:
            source = options['source']
            try:
                # Execute targeted scraping z comprehensive processing
                self.stdout.write(f"Starting scraping from {source}...")
                count = service.scrape_single_source(source)
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully scraped {count} unique articles from {source}")
                )
            except Exception as e:
                # Convert to CommandError dla user-friendly error handling
                raise CommandError(f"Error scraping {source}: {e}")
        
        # OPERATION MODE 3: Batch Scraping All Sources
        elif options['all']:
            self.stdout.write("Starting comprehensive batch scraping...")
            # Execute batch scraping z wszystkich registered sources
            results = service.scrape_all_sources()
            total = sum(results.values())
            
            # Display detailed per-source results
            self.stdout.write("\nScraping results:")
            for source, count in results.items():
                if count > 0:
                    self.stdout.write(f"  {source}: {count} unique articles")
                else:
                    self.stdout.write(self.style.WARNING(f"  {source}: 0 articles (check for errors)"))
            
            self.stdout.write(
                self.style.SUCCESS(f"\nTotal unique articles scraped: {total}")
            )
        
        else:
            # No valid operation mode specified
            raise CommandError(
                "Please specify an operation:\n"
                "  --source <name>     Scrape specific source\n"
                "  --all               Scrape all sources\n"
                "  --list-sources      List available sources"
            )
        
        # ENHANCEMENT: AI-Powered Summary Generation (optional)
        if options['generate_summary']:
            self.stdout.write("\nGenerating AI-powered blog summaries...")
            
            # Generate daily summary dla recent articles
            self.stdout.write("Creating daily summary...")
            daily_summary = service.generate_daily_summary()
            
            # Generate weekly summary dla broader perspective
            self.stdout.write("Creating weekly summary...")
            weekly_summary = service.generate_weekly_summary()
            
            # Report summary generation results
            if daily_summary:
                self.stdout.write(self.style.SUCCESS(f"✓ Daily summary: {daily_summary.title}"))
            else:
                self.stdout.write(self.style.WARNING("⚠ No daily summary created (no recent articles)"))
                
            if weekly_summary:
                self.stdout.write(self.style.SUCCESS(f"✓ Weekly summary: {weekly_summary.title}"))
            else:
                self.stdout.write(self.style.WARNING("⚠ No weekly summary created (insufficient articles)"))
        
        # REPORTING: Final System Statistics
        stats = service.get_statistics()
        self.stdout.write("\n" + "="*50)
        self.stdout.write("SYSTEM STATISTICS")
        self.stdout.write("="*50)
        self.stdout.write(f"  Total articles in database: {stats['total_articles']}")
        self.stdout.write(f"  Unique articles (post-deduplication): {stats['unique_articles']}")
        self.stdout.write(f"  Detected duplicates: {stats['duplicates']}")
        self.stdout.write(f"  Deduplication efficiency: {stats['duplicate_rate']:.1f}%")
        self.stdout.write(f"  Active sources: {len(stats['source_statistics'])}")
        self.stdout.write(f"  Generated summaries: {stats['total_summaries']}")
        self.stdout.write("="*50)