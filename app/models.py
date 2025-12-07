from django.conf import settings
from django.db import models
from django.core.validators import MaxLengthValidator
from django.db.models.signals import post_save
from django.dispatch import receiver


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

    name = models.CharField(max_length=100, blank=True, default="")
    bio = models.TextField(blank=True, default="", validators=[MaxLengthValidator(1000)])
    interests = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=50, default="Member")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")

    nickname = models.CharField(max_length=64, blank=True, default="")
    sustainability_interests = models.JSONField(default=list, blank=True)
    onboarding_complete = models.BooleanField(default=False)

    def __str__(self):
        return self.user.get_username()

    @property
    def display_name(self) -> str:
        """
        Display priority:
        1) nickname (if set)
        2) Google name via Django User first_name/last_name
        3) username
        """
        if self.nickname:
            return self.nickname
        full = self.user.get_full_name()
        if full:
            return full
        return self.user.get_username()


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile_exists(sender, instance, created, **kwargs):
    """
    Ensure every user has a Profile row. If a profile already exists, do nothing.
    """
    Profile.objects.get_or_create(user=instance)


class Post(models.Model):
    CATEGORIES = [
        ('books', 'Books'),
        ('electronics', 'Electronics'),
        ('clothing', 'Clothing'),
        ('furniture', 'Furniture'),
        ('tickets', 'Tickets'),
        ('kitchen', 'Kitchen Items'),
        ('other', 'Other'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(validators=[MaxLengthValidator(1000)])
    category = models.CharField(
        max_length=50,
        choices=CATEGORIES,
        default='other'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    hidden_from = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="posts_hidden_from",
        help_text="Users who should NOT be able to see this post.",
    )

    def __str__(self):
        return self.title


class PostImages(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='posts/')


class PostFlag(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="flags")
    flagged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Flag on {self.post.title} by {self.flagged_by.username}"