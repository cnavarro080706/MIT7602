import uuid
from django.db import models
from django.utils.timezone import now

class BugReport(models.Model):
    bug_id = models.CharField(max_length=20, unique=True, default=None, editable=False)
    description = models.TextField()
    date_submitted = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.bug_id:
            self.bug_id = f"BUG-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

class BugComment(models.Model):
    bug = models.ForeignKey(BugReport, on_delete=models.CASCADE, related_name="comments")
    comment = models.TextField()
    commented_at = models.DateTimeField(auto_now_add=True)