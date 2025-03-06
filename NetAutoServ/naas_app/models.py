from django.db import models
from django.contrib.auth.models import User

class AutomationRun(models.Model):
    status = models.CharField(max_length=20, choices=[
        ('STARTED', 'Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed')
    ], default='STARTED')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    log_file = models.TextField(blank=True, default="")
    logged_user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return f"Run {self.id} - {self.status}"
    
class Log(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=255)
    status = models.CharField(max_length=50)
    details = models.TextField()
    logged_user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return f"{self.timestamp} - {self.action} - {self.status}"

class Configuration(models.Model):
    hostname = models.CharField(max_length=255)
    filepath = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    logged_user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name="naas_configurations")

    def __str__(self):
        return f"{self.hostname} - {self.created_at}"