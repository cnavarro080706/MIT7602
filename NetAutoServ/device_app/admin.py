from django.contrib import admin
from .models import Device
from .models import Interface
from .models import Topology
from .models import Configuration

# Register your models here.
admin.site.register(Device)
admin.site.register(Interface)
admin.site.register(Topology)
admin.site.register(Configuration)