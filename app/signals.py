# app/signals.py
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from allauth.account.signals import user_logged_in

from .models import Profile

User = get_user_model()


@receiver(post_save, sender=User, dispatch_uid="app_profile_ensure_one")
def ensure_profile(sender, instance, created, **kwargs):
    """
    Idempotent: guarantees a Profile exists for every User.
    Using get_or_create prevents UNIQUE constraint errors even if
    the signal is accidentally registered twice.
    """
    Profile.objects.get_or_create(user=instance)


@receiver(user_logged_in, dispatch_uid="app_assign_role_on_login")
def assign_role_on_login(request, user, **kwargs):
    """
    Set role on login from ?role=... but never allow privilege escalation.
    """
    role = (request.GET.get("role") or "member").lower()
    profile, _ = Profile.objects.get_or_create(user=user)

    if role == "organizer" and (user.is_staff or user.is_superuser):
        profile.role = "organizer"
    else:
        profile.role = "member"

    profile.save(update_fields=["role"])
