from django.core.management.base import BaseCommand, CommandError
from ai_news.src.news_service import NewsOrchestrationService


class Command(BaseCommand):
    help = 'Generate blog summaries from scraped articles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['daily', 'weekly'],
            default='daily',
            help='Type of summary to generate (daily or weekly)',
        )
        parser.add_argument(
            '--topic',
            type=str,
            default='AI News',
            help='Topic category for the summary',
        )

    def handle(self, *args, **options):
        service = NewsOrchestrationService()
        summary_type = options['type']
        topic = options['topic']
        
        self.stdout.write(f"Generating {summary_type} summary for topic: {topic}")
        
        try:
            if summary_type == 'daily':
                summary = service.generate_daily_summary(topic)
            else:
                summary = service.generate_weekly_summary(topic)
            
            if summary:
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully generated summary: {summary.title}")
                )
                self.stdout.write(f"Summary ID: {summary.id}")
                self.stdout.write(f"Articles included: {summary.articles.count()}")
                
                # Display preview of summary
                preview = summary.summary[:200] + "..." if len(summary.summary) > 200 else summary.summary
                self.stdout.write(f"\nPreview:\n{preview}")
            else:
                self.stdout.write(
                    self.style.WARNING("No summary generated - possibly no new articles found")
                )
        
        except Exception as e:
            raise CommandError(f"Error generating summary: {e}")