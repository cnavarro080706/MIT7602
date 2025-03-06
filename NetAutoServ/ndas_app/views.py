from django.shortcuts import render, redirect
from user_app.models import User, UserActivityLog
from device_app.models import Device
from compliance_app.models import ComplianceResult
from emulator_app.models import EmulatorSession 
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.contrib import messages


def home_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    context = {}                                                # Redirect to the dashboard if the user is logged in
    return render(request, 'ndas_app/index.html', context)      # Render the public index page for non-logged-in users

@login_required
def dashboard(request):
    if request.user.is_superuser:
        # Admin can see all data
        total_devices = Device.objects.count()
        total_users = User.objects.count()
        total_logs = UserActivityLog.objects.count()
        total_compliance_checks = ComplianceResult.objects.count()
        logs = UserActivityLog.objects.order_by("timestamp")[:10]
        total_simulated_devices = EmulatorSession.objects.filter(status="Running").count()
        total_tested_devices = EmulatorSession.objects.filter(status="Running").count()
    else:
        # Regular users can only see their own data
        total_devices = Device.objects.filter(logged_user=request.user).count()
        total_users = User.objects.filter(id=request.user.id).count()
        total_logs = UserActivityLog.objects.filter(user=request.user).count()
        total_compliance_checks = ComplianceResult.objects.filter(logged_user=request.user).count()
        logs = UserActivityLog.objects.filter(user=request.user).order_by("timestamp")[:10]
        total_simulated_devices = EmulatorSession.objects.filter(logged_user=request.user, status="Running").count()
        total_tested_devices = EmulatorSession.objects.filter(logged_user=request.user, status="Running").count()

    # Get recent activity logs (for Chart.js)
    activity_dates = [log.timestamp.strftime("%Y-%m-%d") for log in logs]
    activity_counts = [UserActivityLog.objects.filter(timestamp__date=log.timestamp.date()).count() for log in logs]

    context = {
        "total_devices": total_devices,
        "total_users": total_users,
        "total_logs": total_logs,
        "total_compliance_checks": total_compliance_checks,
        "activity_dates": activity_dates,
        "activity_counts": activity_counts,
        "total_simulated_devices": total_simulated_devices,
        "total_tested_devices": total_tested_devices,
    }

    return render(request, "ndas_app/dashboard.html", context)
