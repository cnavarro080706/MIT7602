from django.urls import path
from . import views
from django.contrib.auth import views as auth_view
from django.conf import settings
from django.conf.urls.static import static
from .views import get_unread_log_count

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name="login"),
    path('profile/', views.user_profile, name='profile'),
    path('invalid/', views.invalid, name='invalid'),
    path('logout/', auth_view.LogoutView.as_view(template_name='user_app/logout.html'), name='logout' ),
    path('activity-logs/', views.activity_logs, name='activity_logs'),
    path("get-unread-log-count/", get_unread_log_count, name="get_unread_log_count"),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
