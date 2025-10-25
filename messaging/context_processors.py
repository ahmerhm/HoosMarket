# messaging/context_processors.py
from .models import Thread, ThreadRead

def messaging_badge(request):
    """
    Adds messages_unread_total to every template (for logged-in users).
    """
    total = 0
    u = getattr(request, "user", None)
    if u and u.is_authenticated:
        threads = (Thread.objects
                   .filter(participants=u)
                   .prefetch_related('messages', 'messages__sender'))
        # compute total unread across threads
        from django.utils import timezone
        for t in threads:
            tr, _ = ThreadRead.objects.get_or_create(thread=t, user=u)
            total += t.messages.exclude(sender=u).filter(created_at__gt=tr.last_read_at).count()
    return {"messages_unread_total": total}
