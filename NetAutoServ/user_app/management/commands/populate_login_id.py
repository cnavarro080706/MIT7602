from django.core.management.base import BaseCommand
from user_app.models import Profile  # Correct import path
import uuid

class Command(BaseCommand):
    help = 'Populate empty login_id fields in the Profile model'

    def handle(self, *args, **kwargs):
        profiles = Profile.objects.filter(login_id='')
        for profile in profiles:
            profile.login_id = str(uuid.uuid4())[:8]
            profile.save()
            self.stdout.write(self.style.SUCCESS(f'Updated login_id for {profile.user.username}'))