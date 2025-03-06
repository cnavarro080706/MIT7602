from django.urls import path
from . import views

urlpatterns = [
    path('emulator/', views.emulator_home, name='emulator_home'),
    path("emulator/device-status/", views.device_status, name="device_status"),
    path('emulator/start/', views.start_emulator, name='start_emulator'),
    path('emulator/stop/', views.stop_emulator, name='stop_emulator'),
    path('emulator/add-connection/', views.add_connection, name='add_connection'),
    path('emulator/update-position/', views.update_position, name='update_position'),
    path('emulator/create-connection/', views.create_connection, name='create_connection'),
    path('get-container-logs/', views.get_container_logs, name='get_container_logs'),
    path('container-status/', views.get_container_status, name='container-status'),
    path('emulator/connect/', views.connect_devices, name='connect_devices'),
    path('emulator/delete_connection/', views.delete_connection, name='delete_connection'),
]