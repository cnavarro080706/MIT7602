from django.contrib import admin
from .models import DeviceConfiguration, EmulatorSession, DeviceConnection, DevicePosition

# Register your models here.
admin.site.register(DeviceConfiguration)
admin.site.register(EmulatorSession)
admin.site.register(DeviceConnection)
admin.site.register(DevicePosition)