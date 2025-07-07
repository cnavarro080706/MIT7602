from django import forms
from .models import BugReport, BugComment

class BugReportForm(forms.ModelForm):
    class Meta:
        model = BugReport
        fields = ['description']

class BugCommentForm(forms.ModelForm):
    class Meta:
        model = BugComment
        fields = ['comment']