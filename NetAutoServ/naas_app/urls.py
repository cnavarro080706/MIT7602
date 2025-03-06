from django.urls import path
from . import views

urlpatterns = [
    path('naas/', views.index, name='naas'),
    path('naas/<int:device_id>/', views.index, name='naas'),
    path('naas/run-automation/<int:device_id>/', views.run_automation, name='run_automation'),
    path('naas/get-status-log/', views.get_status_log, name='get_status_log'),
    path('naas/stream-logs/', views.stream_logs, name='stream_logs'),
]
