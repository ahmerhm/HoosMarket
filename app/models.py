from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

class Profile(models.Model):
    ROLE_CHOICES = [
        ("member", "Member"),
        ("organizer", "Organizer"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    bio = models.TextField(blank=True, default="")
    interests = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=50, default="Member")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")

    def __str__(self):
        return self.user.get_username()


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile_exists(sender, instance, created, **kwargs):
    """
    Ensure every user has a Profile row. If a profile already exists, do nothing.
    """
    Profile.objects.get_or_create(user=instance)

