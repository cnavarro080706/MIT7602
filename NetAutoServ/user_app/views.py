from django.shortcuts import render, redirect, HttpResponse
from .forms import UserRegistrationForm, LoginForm
from django.contrib import messages
from django.contrib.auth import authenticate, login
from .forms import UserRegistrationForm, LoginForm, UserUpdateForm, ProfileUpdateForm
from django.contrib.auth.decorators import login_required
from .models import UserActivityLog, Profile
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
import secrets
from django.core.mail import send_mail
from django.utils.timezone import now, timedelta
from django.contrib.auth.models import User
from django.urls import reverse
from django.template.loader import render_to_string
from device_app.models import Device
from django.http import JsonResponse
from django.conf import settings
from django.db.models import Count, Sum
import os
import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth import get_user_model
from django.middleware.csrf import get_token
from .utils import send_custom_email,send_password_reset_confirmation
from django.utils.html import strip_tags

import logging

logger = logging.getLogger(__name__)

def assign_all_permissions(user):
    """Assign all available permissions to the newly created user."""
    permissions = Permission.objects.all()  # Get all permissions
    user.user_permissions.set(permissions)  # Assign all permissions
    user.save()
    print(f"All permissions assigned to {user.username}")

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
            assign_all_permissions(new_user) 

            Profile.objects.create(user=new_user)
            context = {'message': 'Registration successful'}
            messages.success(request, f'Your account {new_user.username} is created successfully!',)
            
            logger.info(f"New user registered: {new_user.username} (Login ID: {new_user.profile.login_id})")
            print("Registration successful. Redirecting to login page.")
            return redirect('login')

        else:
            messages.error(request, "Error")
            print("Form is not valid")
    else:
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

    device_counts = UserActivityLog.objects.values("user__username").annotate(total_devices=Count("device", distinct=True))
    time_spent = UserActivityLog.objects.values("user__username").annotate(total_time=Sum("timestamp"))

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
        'log_entries': log_entries, 
        'device_counts': device_counts,
        'time_spent': time_spent,
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
    user = request.user  # Avoid repeated lookups
    profile_instance = user.profile  # Get profile once

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = ProfileUpdateForm(
            request.POST, 
            request.FILES, 
            instance=profile_instance
        )

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            
            # Log activity
            UserActivityLog.objects.create(
                user=user,
                action="Profile updated",
                description=f"Updated profile details and/or image."
            )
            
            messages.success(request, 'Your profile has been updated!')
            logger.info(
                f"User profile updated: {user.username} "
                f"(Login ID: {profile_instance.login_id})"
            )
            return redirect('profile')

    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = ProfileUpdateForm(instance=profile_instance)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    return render(request, 'profile.html', context)

def log_activity(user, action, device=None):
    """Logs user activity with an optional device description."""
    description = f"Started testing device {device.hostname}" if device else "No device specified"
    
    UserActivityLog.objects.create(
        user=user,
        action=action,
        description=description
    )

@csrf_exempt
def forgot_password(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        logger.info("Received forgot password request")

        data = json.loads(request.body)
        email = data.get("email")
        username = data.get("username")

        if not email or not username:
            return JsonResponse({"error": "Email and username are required."}, status=400)

        try:
            user = User.objects.get(email=email, username=username)
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

        # Generate token & encoded user ID
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        # Generate reset URL
        reset_url = request.build_absolute_uri(reverse("reset_password", kwargs={"uidb64": uidb64, "token": token}))

        print("Generated Reset URL:", reset_url)

        # Render HTML email
        html_message = render_to_string(
            "user_app/email_reset_password.html",
            {"reset_link": reset_url, "user": user, "token_valid": True}
        )

        # Strip HTML for text version
        text_message = strip_tags(html_message)

        # Send email
        send_custom_email("Password Reset Request", html_message, [email], use_pw_reset=True)

        return JsonResponse({"message": "A reset link has been sent to your registered email."})

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format."}, status=400)

User = get_user_model()

@csrf_exempt  # TEMPORARY: Remove this once testing is done
def reset_password(request, uidb64, token):
    logger.info(f"Request method: {request.method}")

    if request.method == "GET":
        # Show the reset password form
        return render(request, "user_app/reset_password.html", {"token_valid": True, "uidb64": uidb64, "token": token})

    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    new_password = request.POST.get("new_password")
    confirm_password = request.POST.get("confirm_password")

    if not new_password or not confirm_password:
        return JsonResponse({"error": "Password is required"}, status=400)

    if new_password != confirm_password:
        return JsonResponse({"error": "Passwords do not match"}, status=400)

    # Decode user ID
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError):
        return JsonResponse({"error": "Invalid user"}, status=400)

    # Check token validity
    if not default_token_generator.check_token(user, token):
        return JsonResponse({"error": "Invalid or expired token"}, status=400)

    # Set new password and save user
    user.set_password(new_password)
    user.save()
    send_password_reset_confirmation(user)
    messages.success(request, "Password reset successful! You can now log in.")
    logger.info(f"Password reset successful for user {user.username}")
    return redirect("login")
