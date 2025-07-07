from django.shortcuts import render, redirect, get_object_or_404
from user_app.models import User, UserActivityLog
from device_app.models import Device
from compliance_app.models import ComplianceResult
from emulator_app.models import EmulatorSession
from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F, Max, Sum, Value
from django.http import JsonResponse
from django.utils import timezone
from django.db.models.functions import TruncDate, Coalesce
import logging


# Configure logging
logger = logging.getLogger(__name__)

def home_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    context = {}                                                # Redirect to the dashboard if the user is logged in
    return render(request, 'ndas_app/index.html', context)      # Render the public index page for non-logged-in users

@login_required
def dashboard(request):
    # Admin specific logic
    if request.user.is_superuser:
        # Admin can see all data
        total_devices = Device.objects.count()
        total_users = User.objects.count()
        total_logs = UserActivityLog.objects.count()
        total_compliance_checks = ComplianceResult.objects.count()
        logs = UserActivityLog.objects.order_by("timestamp")[:10]
        total_simulated_devices = EmulatorSession.objects.filter(status="Running").count()
        total_tested_devices = EmulatorSession.objects.aggregate(
            total_tests=Sum("start_count")
        ).get("total_tests") or 0 
        total_time_spent = EmulatorSession.objects.aggregate(
            total_time=Sum("duration")
        )["total_time"] or 0.0
        
        time_spent = (
            EmulatorSession.objects
            .values(username=Coalesce('logged_user__username', Value('devuser'))) 
            .annotate(total_time=Sum("duration"))
            .order_by("-total_time")
        )
        # Add this new query for device testing details
        tested_devices = (
            EmulatorSession.objects
            .select_related('device', 'logged_user')
            .values(
                device_name=F('device__hostname'),
                device_status=F('status'))
            .annotate(
                total_tests=Sum('start_count'),
                total_duration=Sum("duration"),
                last_tested_by=Max('logged_user__username'),
                last_duration=Max('duration'),
                last_tested_at=Max('end_time'),
            )
            .order_by('-total_tests')
        )
        # Query for tested devices per user
        tested_devices_per_user = (
            EmulatorSession.objects
            .values(logged_user__username=Coalesce('logged_user__username', Value('devuser')))
            .annotate(total_tests=Sum('start_count'))
            .order_by('-total_tests')
        )
        
    else:
        # Regular users can only see their own data
        total_devices = Device.objects.filter(logged_user=request.user).count()
        total_users = User.objects.filter(id=request.user.id).count()
        total_logs = UserActivityLog.objects.filter(user=request.user).count()
        total_compliance_checks = ComplianceResult.objects.filter(logged_user=request.user).count()
        logs = UserActivityLog.objects.filter(user=request.user).order_by("timestamp")[:10]
        total_simulated_devices = EmulatorSession.objects.filter(logged_user=request.user, status="Running").count()
        total_tested_devices = EmulatorSession.objects.filter(logged_user=request.user).aggregate(
            total_tests=Sum("start_count")
        ).get("total_tests") or 0
        total_time_spent = EmulatorSession.objects.filter(logged_user=request.user).aggregate(
            total_time=Sum("duration")
        )["total_time"] or 0.0

        time_spent = (
            EmulatorSession.objects
            .values(username=Coalesce('logged_user__username', Value('devuser'))) 
            .annotate(total_time=Sum("duration"))
            .order_by("-total_time")
        )
        # Add this new query for device testing details
        tested_devices = (
        EmulatorSession.objects
        .select_related('device', 'logged_user')
        .values(
            device_name=F('device__hostname'),
            device_status=F('status'))
        .annotate(
            total_tests=Sum('start_count'),
            total_duration=Sum("duration"),
            last_tested_by=Max('logged_user__username'),
            last_duration=Max('duration'),
            last_tested_at=Max('end_time'),
        )
        .order_by('-total_tests')
    )
        # Query for tested devices per user
        tested_devices_per_user = (
            EmulatorSession.objects
            .values(logged_user__username=Coalesce('logged_user__username', Value('devuser')))
            .annotate(total_tests=Sum('start_count'))
            .order_by('-total_tests')
        )

    # Optimized user activity log data
    activity_data = (
        UserActivityLog.objects.values(date=TruncDate("timestamp"))
        .annotate(count=Count("id"))
        .order_by("date")
    )  

    # Get recent activity logs (for Chart.js)
    activity_dates = [data["date"].strftime("%Y-%m-%d") for data in activity_data]
    activity_counts = [data["count"] for data in activity_data]

    # Device activity per user
    device_counts = (
    Device.objects
    .values(logged_user__username=Coalesce('logged_user__username', Value('devuser')))
    .annotate(total_devices=Count("id")))

    #   Get the device counts for each user
    top_tested_devices = tested_devices[:8] 

    context = {
        "logs": logs,
        "total_devices": total_devices,
        "total_users": total_users,
        "total_logs": total_logs,
        "total_compliance_checks": total_compliance_checks,
        "activity_dates": activity_dates,
        "activity_counts": activity_counts,
        "total_simulated_devices": total_simulated_devices,
        "total_tested_devices": total_tested_devices,
        "device_counts": list(device_counts),
        "total_time_spent": total_time_spent,
        "time_spent": list(time_spent),
        "tested_devices": tested_devices,
        "tested_device_labels": [d["device_name"] for d in top_tested_devices],
        "tested_device_counts": [d["total_tests"] or 0 for d in top_tested_devices],
        "tested_device_durations": [round((d["total_duration"] or 0) / 60, 1) for d in tested_devices], 
        # "tested_device_durations": [round(d["total_duration"], 2) if d["total_duration"] else 0 for d in tested_devices],
        "tested_devices_per_user": tested_devices_per_user,
        "usernames": [d['logged_user__username'] for d in tested_devices_per_user],
        "total_tests_per_user": [d['total_tests'] for d in tested_devices_per_user],
        "device_status": [d["device_status"] for d in tested_devices],
    }
    
    return render(request, "ndas_app/dashboard.html", context)

# Helper function to format duration in minutes to days, hrs
def convert_duration(minutes):
    days = minutes // (24 * 60)
    hours = (minutes % (24 * 60)) // 60
    minutes_remaining = minutes % 60

    if days > 0:
        return f"{days} day(s), {hours} hour(s)"
    elif hours > 0:
        return f"{hours} hour(s), {minutes_remaining} minute(s)"
    else:
        return f"{minutes_remaining} minute(s)"