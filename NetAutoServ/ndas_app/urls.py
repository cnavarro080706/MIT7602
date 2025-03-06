
from django.urls import path
from . import views

# app_name = 'ndas_app'

urlpatterns = [
    path('', views.home_view, name='index'),                    # Public index page for non-logged-in users
    path('dashboard/', views.dashboard, name='dashboard'),      # Dashboard page for logged-in users
]