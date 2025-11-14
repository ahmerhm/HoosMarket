from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from allauth.account.signals import user_logged_in
from allauth.socialaccount.models import SocialAccount

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


def _split_full_name(name: str):
    """
    Best-effort split of a full name into (first, last).
    If there's only one token, treat it as first name.
    """
    if not name:
        return "", ""
    parts = name.strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


@receiver(user_logged_in, dispatch_uid="app_sync_google_name_on_login")
def sync_google_name_on_login(request, user, **kwargs):
    """
    On Google login, populate User.first_name / User.last_name if they are empty.
    This does NOT touch Profile.nickname (which overrides display via Profile.display_name).
    """
    try:
        sa = SocialAccount.objects.filter(user=user, provider="google").first()
        if not sa:
            return

        data = sa.extra_data or {}
        given = (data.get("given_name") or "").strip()
        family = (data.get("family_name") or "").strip()
        fallback_full = (data.get("name") or "").strip()

        if (not given and not family) and fallback_full:
            given, family = _split_full_name(fallback_full)

        to_update = []
        if not user.first_name and given:
            user.first_name = given
            to_update.append("first_name")
        if not user.last_name and family:
            user.last_name = family
            to_update.append("last_name")

        if to_update:
            user.save(update_fields=to_update)
    except Exception:
        pass
