from django.urls import path
from . import views
from django.contrib.auth import views as auth_view
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name="login"),
    path('profile/', views.user_profile, name='profile'),
    path('invalid/', views.invalid, name='invalid'),
    path('logout/', auth_view.LogoutView.as_view(template_name='user_app/logout.html'), name='logout' ),
    path('activity-logs/', views.activity_logs, name='activity_logs'),
    path('get-unread-log-count/', views.get_unread_log_count, name='get_unread_log_count'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', views.reset_password, name='reset_password'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
