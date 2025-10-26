from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from datetime import datetime, timezone as dt_timezone  # for a safe "very old" default

User = settings.AUTH_USER_MODEL


def epoch_aware():
    """A safe 'very old' timestamp for last_read_at defaults."""
    return datetime(1970, 1, 1, tzinfo=dt_timezone.utc)


class Thread(models.Model):
    # Participants (works for DMs and groups)
    participants = models.ManyToManyField(User, related_name='threads')

    # --- DM uniqueness (Only set for 1:1 threads) ---
    # unique key for (min_id:max_id). Enforces one thread per user pair.
    pair_key = models.CharField(max_length=64, unique=True, blank=True, null=True)

    # --- Group fields (NEW) ---
    is_group = models.BooleanField(default=False)
    name = models.CharField(max_length=120, blank=True, null=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='threads_created'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.is_group and self.name:
            return f"Group: {self.name}"
        return f"Thread {self.pk}"

    # ---------- DMs ----------
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
        - Ignores group threads (is_group=False).
        """
        if user_a == user_b:
            raise ValueError("Cannot create a thread with yourself.")

        key = Thread._pair_key_for(user_a.id, user_b.id)

        # 1) Fast path: already keyed DM thread
        existing = Thread.objects.filter(pair_key=key, is_group=False).first()
        if existing:
            return existing, False

        # 2) Legacy fallback: find an old 1:1 thread (no pair_key yet)
        legacy = (
            Thread.objects
            .filter(is_group=False, participants=user_a)
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
                already = Thread.objects.select_for_update().filter(pair_key=key, is_group=False).first()
                if already:
                    return already, False
                legacy.pair_key = key
                legacy.save(update_fields=['pair_key'])
            return legacy, False

        # 3) Create the DM thread (unique constraint prevents duplicates under concurrency)
        with transaction.atomic():
            # Double-check no one created it in the meantime
            existing = Thread.objects.select_for_update().filter(pair_key=key, is_group=False).first()
            if existing:
                return existing, False
            t = Thread.objects.create(pair_key=key, is_group=False)
            t.participants.add(user_a, user_b)
        return t, True

    # ---------- Groups ----------
    @staticmethod
    def create_group(name, creator, members):
        """
        Create a group thread with a name and members (iterable of User instances).
        Includes the creator automatically (if not present).
        pair_key remains NULL for groups.
        """
        with transaction.atomic():
            t = Thread.objects.create(is_group=True, name=name, created_by=creator)
            # include creator
            t.participants.add(creator)
            for m in members:
                if m.id != creator.id:
                    t.participants.add(m)
        return t


class Message(models.Model):
    thread = models.ForeignKey(Thread, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, related_name='messages_sent', on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']  # oldest -> newest for display

    def __str__(self):
        return f"Msg {self.pk} by {self.sender}"


class ThreadRead(models.Model):
    """
    Per-user "last read" marker for a thread.
    Used to compute unread counts and show badges.
    """
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='reads')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='thread_reads')
    last_read_at = models.DateTimeField(default=epoch_aware)

    class Meta:
        unique_together = ('thread', 'user')

    def __str__(self):
        return f"ThreadRead(thread={self.thread_id}, user={self.user_id}, last_read_at={self.last_read_at})"
