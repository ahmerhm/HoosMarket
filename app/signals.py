from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from allauth.account.signals import user_logged_in
from .models import Profile

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Create or update user profile whenever a User is saved."""
    if created:
        Profile.objects.create(user=instance)
    else:
        Profile.objects.get_or_create(user=instance)  
        instance.profile.save()

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

@receiver(user_logged_in)
def assign_role_on_login(request, user, **kwargs):
    role = request.GET.get("role")
    profile, _ = Profile.objects.get_or_create(user=user)

    # Prevent anyone from setting themselves as organizer
    if role == "organizer":
        # Only allow organizer role if admin pre-approved them
        if user.is_staff or user.is_superuser:
            profile.role = "organizer"
        else:
            profile.role = "member"  # downgrade to member automatically
    else:
        profile.role = "member"

    profile.save()