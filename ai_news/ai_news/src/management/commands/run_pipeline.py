# Django management command framework
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
import time


class Command(BaseCommand):
    """
    Django management command dla uruchamiania pełnego AI News Pipeline.
    
    Wygodny wrapper dla PipelineRunner z pełną integracją Django management system.
    Alternatywa dla bezpośredniego uruchamiania pipeline_runner.py z lepszą integracją
    z Django ecosystem.
    
    Features:
    - Pełny pipeline z dependency injection
    - Environment loading z .env
    - Opcjonalne AI summarization
    - Comprehensive error handling
    - Django-style output formatting
    - Progress reporting i statistics
    
    Wykorzystywany przez:
    - Scheduled tasks i cron jobs
    - Manual pipeline execution
    - Development i testing
    - System administration
    
    Example Usage:
    python manage.py run_pipeline                    # Pełny pipeline
    python manage.py run_pipeline --no-summary      # Bez AI summarization
    python manage.py run_pipeline --stats-only      # Tylko statystyki
    python manage.py run_pipeline --interactive     # Interactive mode
    """
    
    help = 'Run complete AI News processing pipeline with dependency injection'

    def add_arguments(self, parser):
        """
        Configure command-line arguments dla pipeline execution.
        
        Args:
            parser: Django ArgumentParser instance
        """
        parser.add_argument(
            '--no-summary',
            action='store_true',
            help='Skip AI summary generation (faster execution)',
        )
        
        parser.add_argument(
            '--stats-only',
            action='store_true', 
            help='Only display system statistics without scraping',
        )
        
        parser.add_argument(
            '--interactive',
            action='store_true',
            help='Enable interactive mode for queries after pipeline',
        )

    def handle(self, *args, **options):
        """
        Execute pipeline with comprehensive error handling i reporting.
        
        Args:
            *args: Positional arguments (unused)
            **options: Parsed command-line arguments
        """
        try:
            # Import PipelineRunner dla pełnej konfiguracji
            from ai_news.src.pipeline_runner import PipelineRunner
            
            # Initialize z pełną dependency injection
            self.stdout.write("🚀 Initializing AI News Pipeline...")
            runner = PipelineRunner()
            
            # OPERATION MODE: Statistics Only
            if options['stats_only']:
                self.stdout.write("📊 Retrieving system statistics...")
                stats = runner.get_system_statistics()
                self._display_statistics(stats)
                return
            
            # OPERATION MODE: Full Pipeline Execution
            start_time = time.time()
            generate_summary = not options['no_summary']
            
            self.stdout.write("⚡ Starting full AI News processing pipeline...")
            if generate_summary:
                self.stdout.write("🤖 AI summary generation: ENABLED")
            else:
                self.stdout.write("⏭️  AI summary generation: SKIPPED")
            
            # Execute complete pipeline
            results = runner.run_full_pipeline(generate_summary=generate_summary)
            
            # Display comprehensive results
            self._display_results(results, time.time() - start_time)
            
            # OPTIONAL: Interactive Query Mode
            if options['interactive']:
                self._interactive_mode(runner)
                
        except Exception as e:
            raise CommandError(f"Pipeline execution failed: {e}")
    
    def _display_results(self, results: dict, execution_time: float):
        """
        Display comprehensive pipeline results w Django-formatted output.
        
        Args:
            results: Pipeline execution results
            execution_time: Total execution time
        """
        self.stdout.write("\n" + "="*60)
        self.stdout.write("🎉 PIPELINE EXECUTION COMPLETE")
        self.stdout.write("="*60)
        
        # Execution status
        status = results.get('pipeline_status', 'unknown')
        if status == 'success':
            self.stdout.write(self.style.SUCCESS(f"✅ Status: {status.upper()}"))
        else:
            self.stdout.write(self.style.ERROR(f"❌ Status: {status.upper()}"))
            if 'error' in results:
                self.stdout.write(self.style.ERROR(f"   Error: {results['error']}"))
        
        # Timing information
        pipeline_time = results.get('execution_time', execution_time)
        self.stdout.write(f"⏱️  Execution time: {pipeline_time}s")
        
        # Scraping results
        scraping_results = results.get('scraping_results', {})
        if scraping_results:
            self.stdout.write(f"\n📰 SCRAPING RESULTS:")
            total_articles = sum(scraping_results.values())
            for source, count in scraping_results.items():
                if count > 0:
                    self.stdout.write(f"   ✓ {source}: {count} articles")
                else:
                    self.stdout.write(f"   ⚠ {source}: 0 articles")
            self.stdout.write(f"   📊 Total scraped: {total_articles} articles")
        
        # Database statistics
        unique_articles = results.get('total_unique_articles', 0)
        duplicates = results.get('total_duplicates', 0)
        self.stdout.write(f"\n🗄️  DATABASE STATE:")
        self.stdout.write(f"   📄 Unique articles: {unique_articles}")
        self.stdout.write(f"   🔄 Duplicates detected: {duplicates}")
        if unique_articles + duplicates > 0:
            duplicate_rate = (duplicates / (unique_articles + duplicates)) * 100
            self.stdout.write(f"   📈 Deduplication rate: {duplicate_rate:.1f}%")
        
        # AI Summary results
        daily_summary = results.get('daily_summary')
        weekly_summary = results.get('weekly_summary')
        
        if daily_summary or weekly_summary:
            self.stdout.write(f"\n🤖 AI SUMMARY GENERATION:")
            if daily_summary:
                self.stdout.write(self.style.SUCCESS(f"   ✓ Daily: {daily_summary.title}"))
            if weekly_summary:
                self.stdout.write(self.style.SUCCESS(f"   ✓ Weekly: {weekly_summary.title}"))
        
        self.stdout.write("="*60)
    
    def _display_statistics(self, stats: dict):
        """
        Display detailed system statistics w formatted output.
        
        Args:
            stats: System statistics dictionary
        """
        self.stdout.write("\n" + "="*50)
        self.stdout.write("📊 SYSTEM STATISTICS")
        self.stdout.write("="*50)
        
        # Core statistics
        self.stdout.write(f"📄 Total articles: {stats.get('total_articles', 0)}")
        self.stdout.write(f"✅ Unique articles: {stats.get('unique_articles', 0)}")
        self.stdout.write(f"🔄 Duplicates: {stats.get('duplicates', 0)}")
        self.stdout.write(f"📈 Duplicate rate: {stats.get('duplicate_rate', 0):.1f}%")
        self.stdout.write(f"🤖 Generated summaries: {stats.get('total_summaries', 0)}")
        
        # Source breakdown
        source_stats = stats.get('source_statistics', {})
        if source_stats:
            self.stdout.write(f"\n📰 SOURCE BREAKDOWN:")
            for source, counts in source_stats.items():
                total = counts.get('total', 0)
                unique = counts.get('unique', 0)
                self.stdout.write(f"   {source}: {total} total, {unique} unique")
        
        # Available scrapers
        scrapers = stats.get('available_scrapers', [])
        self.stdout.write(f"\n🔧 Available scrapers: {len(scrapers)}")
        if scrapers:
            self.stdout.write(f"   {', '.join(scrapers)}")
        
        self.stdout.write("="*50)
    
    def _interactive_mode(self, runner):
        """
        Enable interactive query mode dla exploring news database.
        
        Args:
            runner: PipelineRunner instance dla queries
        """
        self.stdout.write("\n" + "="*50)
        self.stdout.write("🔍 INTERACTIVE QUERY MODE")
        self.stdout.write("="*50)
        self.stdout.write("Ask questions about your news database!")
        self.stdout.write("Examples:")
        self.stdout.write("  - What are the latest AI trends?")
        self.stdout.write("  - Find articles about machine learning")
        self.stdout.write("  - Show me database statistics")
        self.stdout.write("\nType 'exit' to quit interactive mode.\n")
        
        while True:
            try:
                query = input("🤖 Query: ").strip()
                
                if query.lower() in ['exit', 'quit', 'q']:
                    self.stdout.write("👋 Exiting interactive mode...")
                    break
                
                if not query:
                    continue
                
                # Process query using AI agent
                self.stdout.write("🔍 Processing query...")
                response = runner.interactive_query(query)
                self.stdout.write(f"\n💬 Response:\n{response}\n")
                
            except KeyboardInterrupt:
                self.stdout.write("\n👋 Interactive mode terminated.")
                break
            except EOFError:
                self.stdout.write("\n👋 Interactive mode terminated.")
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error processing query: {e}"))
