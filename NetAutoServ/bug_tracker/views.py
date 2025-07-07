from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
from .models import BugReport, BugComment
from .forms import BugReportForm, BugCommentForm

def submit_bug(request):
    if request.method == "POST":
        form = BugReportForm(request.POST)
        if form.is_valid():
            bug = form.save()
            send_mail(
                subject=f"New Bug Report: {bug.bug_id}",
                message=f"A new bug has been reported.\n\nBug ID: {bug.bug_id}\nDescription: {bug.description}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=settings.SME_EMAILS
            )
            return redirect("bug_list")
    else:
        form = BugReportForm()
    return render(request, "bug_tracker/submit_bug.html", {"form": form})

def bug_list(request):
    bugs = BugReport.objects.all()
    return render(request, "bug_tracker/bug_list.html", {"bugs": bugs})

def add_comment(request, bug_id):
    bug = get_object_or_404(BugReport, bug_id=bug_id)
    if request.method == "POST":
        form = BugCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.bug = bug
            comment.save()
            return redirect("bug_list")
    else:
        form = BugCommentForm()
    return render(request, "bug_tracker/add_comment.html", {"form": form, "bug": bug})