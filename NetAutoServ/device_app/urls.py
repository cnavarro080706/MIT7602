from django.urls import path
from . import views
from naas_app.views import view_configuration

urlpatterns = [
    path('devices/', views.device_list, name='device_list'),
    path('devices/add-device/', views.add_device, name='add_device'),
    path('devices/edit-device/<int:device_id>/', views.edit_device, name='edit_device'),
    path('devices/delete-device/<int:device_id>/', views.delete_device, name='delete_device'),
    path('view-configuration/<int:device_id>/', view_configuration, name='view_configuration'),

]