from django.core.management.base import BaseCommand
from ai_news.src.news_service import NewsOrchestrationService
from ai_news.models import NewsArticle, BlogSummary


class Command(BaseCommand):
    help = 'Display statistics about scraped news articles and summaries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up old articles (older than 30 days)',
        )
        parser.add_argument(
            '--cleanup-days',
            type=int,
            default=30,
            help='Number of days to keep articles (default: 30)',
        )

    def handle(self, *args, **options):
        service = NewsOrchestrationService()
        
        # Display current statistics
        stats = service.get_statistics()
        
        self.stdout.write(self.style.SUCCESS("=== News Scraper Statistics ===\n"))
        
        self.stdout.write(f"Total Articles: {stats['total_articles']}")
        self.stdout.write(f"Unique Articles: {stats['unique_articles']}")
        self.stdout.write(f"Duplicate Articles: {stats['duplicates']}")
        self.stdout.write(f"Duplicate Rate: {stats['duplicate_rate']:.1f}%")
        self.stdout.write(f"Total Summaries: {stats['total_summaries']}")
        
        self.stdout.write("\n=== Available Scrapers ===")
        for scraper in stats['available_scrapers']:
            self.stdout.write(f"  - {scraper}")
        
        self.stdout.write("\n=== Source Statistics ===")
        for source, source_stats in stats['source_statistics'].items():
            self.stdout.write(
                f"  {source}: {source_stats['unique']} unique / {source_stats['total']} total"
            )
        
        # Display recent summaries
        self.stdout.write("\n=== Recent Summaries ===")
        recent_summaries = BlogSummary.objects.all()[:5]
        if recent_summaries:
            for summary in recent_summaries:
                self.stdout.write(
                    f"  - {summary.title} ({summary.created_date.strftime('%Y-%m-%d')})"
                )
        else:
            self.stdout.write("  No summaries found")
        
        # Cleanup if requested
        if options['cleanup']:
            days = options['cleanup_days']
            self.stdout.write(f"\nCleaning up articles older than {days} days...")
            cleaned_count = service.cleanup_old_articles(days)
            self.stdout.write(
                self.style.SUCCESS(f"Cleaned up {cleaned_count} old articles")
            )