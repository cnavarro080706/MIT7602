from django.contrib import admin
from .models import Profile, UserActivityLog

# Register your models here.
admin.site.register(Profile)
admin.site.register(UserActivityLog)