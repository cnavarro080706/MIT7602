from django.shortcuts import render, redirect, HttpResponse
from .forms import UserRegistrationForm, LoginForm
from django.contrib import messages
from django.contrib.auth import authenticate, login
from .forms import UserRegistrationForm, LoginForm, UserUpdateForm, ProfileUpdateForm
from django.contrib.auth.decorators import login_required
from .models import UserActivityLog, Profile
from django.http import JsonResponse
from django.conf import settings
import os

import logging

logger = logging.getLogger(__name__)

# Create your views here.
def register(request):
    print("Request method:", request.method)
    
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST) 
        print("Form validation status:", user_form.is_valid())
        
        if user_form.is_valid():
            new_user = user_form.save(commit=False)
            new_user.set_password(user_form.cleaned_data['password'])
            new_user.save()
            # Profile.objects.create(user=new_user)
            messages.success(request, 'Your account is created successfully!',)
            logger.info(f"New user registered: {new_user.username} (Login ID: {new_user.profile.login_id})")
            return redirect('login')
            # return render(request, 'users/register_success.html', context)
        else:
            messages.error(request, "Error")
            print("Form is not valid")
    else:
        print("GET request, rendering empty form")
        user_form = UserRegistrationForm()
    
    context = {
        'user_form': user_form,
        }
    print("Rendering registration page")
    return render(request, 'user_app/register.html', context)

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user = authenticate(request, username=data['username'], password=data['password'])
            if user is not None:
                login(request, user)
                messages.success(request, (f'login as {user.username}'))
                return redirect('dashboard')
            else:
                return redirect('invalid')
    else:

        form = LoginForm()
    context = {
        'form': form,
    }
    return render(request, 'user_app/login.html', context )

def invalid(request):
    return render(request, 'user_app/invalid.html')

# Profile View (for updating profile and user details)
@login_required
def user_profile(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            # Check if either of the forms has any changes
            if user_form.has_changed() or profile_form.has_changed(): 
                user_form.save()
                profile_form.save()
                messages.success(request, 'Your profile has been updated!')   
            else:
                messages.info(request, 'No changes were made.')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }

    return render(request, 'user_app/profile.html', context)

def log_user_action(user, action, description=""):
    UserActivityLog.objects.create(user=user, action=action, description=description)

@login_required
def activity_logs(request):

    if request.user.is_superuser:
        # Superuser sees all logs
        unread_count = UserActivityLog.objects.filter(is_read=False).count()
        logs = UserActivityLog.objects.all().order_by('-timestamp')
    else:
        # Regular user sees only their logs
        unread_count = UserActivityLog.objects.filter(user=request.user, is_read=False).count()
        logs = UserActivityLog.objects.filter(user=request.user).order_by('-timestamp')

    previous_unread_count = request.session.get('previous_unread_count', unread_count)
    request.session['previous_unread_count'] = unread_count

    # Fetch logs from the database (sorted by most recent first)
    # logs = UserActivityLog.objects.filter(action__icontains='Create').union(
    #     UserActivityLog.objects.filter(action__icontains='Update'),
    #     UserActivityLog.objects.filter(action__icontains='Delete')
    # ).order_by('-timestamp')

    # print(logs.count())

    # Read the automation.log file (Ensure most recent logs appear first)
    auto_log_file_path = os.path.join(settings.BASE_DIR, "automation.log")  # Adjust path if needed
    log_entries = []
    if request.user.is_superuser:  # Only allow admin to access automation.log
        auto_log_file_path = os.path.join(settings.BASE_DIR, "automation.log")  # Adjust path if needed
        if os.path.exists(auto_log_file_path):
            with open(auto_log_file_path, "r") as file:
                log_entries = file.readlines()  # Read file content line by line
            log_entries.reverse()  # Reverse to display most recent logs first

    context = {
        'unread_count': unread_count,
        'previous_unread_count': previous_unread_count,
        'logs': logs,
        'log_entries': log_entries,  # Add log file entries to context (empty for non-admin users)
    }
    return render(request, 'user_app/activity_logs.html', context)

@login_required
def get_unread_log_count(request):
    if request.user.is_superuser:
        # Superuser sees all unread counts
        unread_count = UserActivityLog.objects.filter(is_read=False).count()
    else:
        # Regular user sees only their unread counts
        unread_count = UserActivityLog.objects.filter(user=request.user, is_read=False).count()

    return JsonResponse({"unread_count": unread_count})

@login_required
def profile(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            logger.info(f"User profile updated: {request.user.username} (Login ID: {request.user.profile.login_id})")
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    return render(request, 'profile.html', context)