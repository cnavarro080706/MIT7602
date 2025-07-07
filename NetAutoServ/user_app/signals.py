from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from device_app.models import Device

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance, logged_user=instance)

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()

@receiver(post_save, sender=User)
def assign_all_permissions(sender, instance, created, **kwargs):
    """Automatically assign all permissions to newly created users."""
    if created and not instance.is_staff:  # Exclude staff/admin users
        permissions = Permission.objects.all()  # Fetch all permissions
        instance.user_permissions.set(permissions)  # Assign all permissions
        instance.save()
        print(f"✅ All permissions assigned to {instance.username}")