from django.conf import settings
from django.db import models
from django.db.models import Q

User = settings.AUTH_USER_MODEL

class Thread(models.Model):
    # Two participants for a simple 1:1 chat. Use M2M so you can grow later.
    participants = models.ManyToManyField(User, related_name='threads')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Thread {self.pk}"

    @staticmethod
    def for_users(user_a, user_b):
        """
        Get or create the unique 1:1 thread between two users.
        """
        if user_a == user_b:
            raise ValueError("Cannot create a thread with yourself.")
        # Find any thread that has exactly these two participants
        qs = (Thread.objects
              .filter(participants=user_a)
              .filter(participants=user_b)
              .annotate(count=models.Count('participants'))
              .filter(count=2))
        if qs.exists():
            return qs.first(), False
        t = Thread.objects.create()
        t.participants.add(user_a, user_b)
        return t, True


class Message(models.Model):
    thread = models.ForeignKey(Thread, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, related_name='messages_sent', on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']  # oldest -> newest for display

    def __str__(self):
        return f"Msg {self.pk} by {self.sender}"

