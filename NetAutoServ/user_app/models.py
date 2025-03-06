from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid


# Create your models here.
# Function to generate the upload path within the 'users' app directory
def user_directory_path(instance, filename):
    # file will be uploaded to 'user_app/<username>/<filename>'
    return f'user_app/{instance.user.username}/{filename}'

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(default='default.png', upload_to=user_directory_path, blank=True)
    # login_id = models.CharField(max_length=50, unique=True, blank=False, editable=False, null=False)

    def __str__(self):
        return f'{self.user.username} Profile'

    def save(self, *args, **kwargs):
        if not self.login_id:
            self.login_id = self.generate_unique_login_id()
        super().save(*args, **kwargs)

    def generate_unique_login_id(self):
        """ Generate a unique login ID """
        while True:
            login_id = str(uuid.uuid4())[:8]  # Generate an 8-character unique ID
            if not Profile.objects.filter(login_id=login_id).exists():
                return login_id

# this model will capture the logging activities 
class UserActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.TextField()
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False) 

    def __str__(self):
        return f'{self.user.username} - {self.action} on {self.timestamp}'
