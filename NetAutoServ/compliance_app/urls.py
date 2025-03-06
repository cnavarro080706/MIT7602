from django.urls import path
from . import views

urlpatterns = [
    path("compliance/", views.device_compliance, name="compliance_list"),
    path("compliance/validate_compliance/", views.validate_device_compliance, name="validate_compliance"),
]