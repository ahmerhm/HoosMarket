from django.conf import settings
from django.db import models, transaction

User = settings.AUTH_USER_MODEL

class Thread(models.Model):
    # Two participants for a simple 1:1 chat. Use M2M so you can grow later.
    participants = models.ManyToManyField(User, related_name='threads')

    # NEW: unique key for (min_id:max_id). Enforces one thread per user pair.
    pair_key = models.CharField(max_length=64, unique=True, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Thread {self.pk}"

    @staticmethod
    def _pair_key_for(u1_id, u2_id):
        a, b = sorted([int(u1_id), int(u2_id)])
        return f"{a}:{b}"

    @staticmethod
    def for_users(user_a, user_b):
        """
        Return the unique 1:1 thread for (user_a, user_b), creating it if needed.
        - Reuses existing threads (with or without pair_key).
        - Ensures no duplicates by using a unique pair_key.
        """
        if user_a == user_b:
            raise ValueError("Cannot create a thread with yourself.")

        key = Thread._pair_key_for(user_a.id, user_b.id)

        # 1) Fast path: already keyed thread
        existing = Thread.objects.filter(pair_key=key).first()
        if existing:
            return existing, False

        # 2) Legacy fallback: find an old thread with exactly these two users (no pair_key yet)
        legacy = (
            Thread.objects
            .filter(participants=user_a)
            .filter(participants=user_b)
            .annotate(pcount=models.Count('participants', distinct=True))
            .filter(pcount=2)
            .order_by('-created_at')
            .first()
        )
        if legacy:
            # Backfill the pair_key so future lookups hit the fast path
            with transaction.atomic():
                # If another request created a keyed thread meanwhile, reuse it.
                already = Thread.objects.select_for_update().filter(pair_key=key).first()
                if already:
                    return already, False
                legacy.pair_key = key
                legacy.save(update_fields=['pair_key'])
            return legacy, False

        # 3) Create the thread (unique constraint prevents duplicates under concurrency)
        with transaction.atomic():
            # Double-check no one created it in the meantime
            existing = Thread.objects.select_for_update().filter(pair_key=key).first()
            if existing:
                return existing, False
            t = Thread.objects.create(pair_key=key)
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
