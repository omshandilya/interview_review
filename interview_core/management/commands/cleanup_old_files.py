from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from interview_core.models import UserAnswer, InterviewQuestion


class Command(BaseCommand):
    help = 'Clean up old unanswered questions and orphaned data older than specified days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Delete records older than this many days (default: 90)'
        )

    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)

        # Delete old unanswered questions
        old_unanswered = InterviewQuestion.objects.filter(
            created_at__lt=cutoff_date,
            is_answered=False
        )
        unanswered_count = old_unanswered.count()
        old_unanswered.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f'Cleaned up {unanswered_count} old unanswered questions '
                f'(older than {days} days)'
            )
        )