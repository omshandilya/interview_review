from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import os
from interview_core.models import UserAnswer

class Command(BaseCommand):
    help = 'Clean up old audio files older than specified days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete files older than this many days (default: 30)'
        )

    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        old_answers = UserAnswer.objects.filter(created_at__lt=cutoff_date)
        deleted_count = 0
        
        for answer in old_answers:
            if answer.audio_file and os.path.exists(answer.audio_file.path):
                os.remove(answer.audio_file.path)
                deleted_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {deleted_count} old audio files')
        )