from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404
from django.views.decorators.http import require_POST
from django.utils import timezone

from .models import Thread, Message, ThreadRead
from .forms import MessageForm, GroupCreateForm  # <-- added GroupCreateForm

User = get_user_model()


@login_required
def inbox(request):
    threads = (
        Thread.objects
        .filter(participants=request.user)
        .prefetch_related('participants', 'messages', 'messages__sender')
    )

    rows = []
    for t in threads:
        # for DMs this will be "the other"; for groups it's fine if this is None
        other = next((p for p in t.participants.all() if p.id != request.user.id), None)

        tr, _ = ThreadRead.objects.get_or_create(thread=t, user=request.user)
        unread_count = (
            t.messages.exclude(sender=request.user)
            .filter(created_at__gt=tr.last_read_at)
            .count()
        )

        rows.append({'thread': t, 'other': other, 'unread_count': unread_count})

    return render(request, 'messaging/inbox.html', {'rows': rows, 'title': 'Messages'})


@login_required
def user_list(request):
    """
    Return the partial that lists all users (except me), optionally filtered by ?q=.
    Loaded into the modal via fetch() and renders templates/messaging/_user_list.html
    """
    q = request.GET.get("q", "").strip()
    users = User.objects.exclude(pk=request.user.pk).order_by("username")
    if q:
        users = users.filter(username__icontains=q)
    return render(request, "messaging/_user_list.html", {"users": users})


@login_required
def compose(request, user_id):
    """
    Show a compose page for DM to `other`. If a thread already exists, show it.
    Only create the thread when the user actually sends a message (POST).
    """
    other = get_object_or_404(User, pk=user_id)
    if other.id == request.user.id:
        raise Http404()

    key = Thread._pair_key_for(request.user.id, other.id)
    thread = Thread.objects.filter(pair_key=key).first()

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            if not thread:
                thread, _ = Thread.for_users(request.user, other)
            Message.objects.create(
                thread=thread,
                sender=request.user,
                text=form.cleaned_data['text']
            )
            return redirect('messaging:thread', thread_id=thread.id)
    else:
        form = MessageForm()

    messages_qs = thread.messages.select_related('sender') if thread else []
    title = f"Chat with @{other.username}"
    return render(request, 'messaging/thread.html', {
        'thread': thread,
        'messages': messages_qs,
        'form': form,
        'other': other,
        'title': title,
    })


@login_required
def group_new(request):
    """
    Create a new group chat: name + members (multi-select).
    Appears in all selected members' inboxes immediately.
    """
    if request.method == "POST":
        form = GroupCreateForm(request.POST, me=request.user)
        if form.is_valid():
            name = form.cleaned_data["name"].strip()
            members = list(form.cleaned_data["members"])
            thread = Thread.create_group(name=name, creator=request.user, members=members)
            # Optional: initial system message, if you want:
            # Message.objects.create(thread=thread, sender=request.user, text=f"{request.user.username} created the group")
            return redirect("messaging:thread", thread_id=thread.id)
    else:
        form = GroupCreateForm(me=request.user)

    return render(request, "messaging/group_new.html", {"form": form, "title": "New group"})


@login_required
@require_POST
def start_with(request):
    """
    OLD behavior created threads immediately. NEW: just go to compose.
    """
    user_id = request.POST.get("user_id")
    other = get_object_or_404(User, pk=user_id)
    return redirect('messaging:compose', user_id=other.id)


@login_required
def thread_detail(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
    if not thread.participants.filter(pk=request.user.pk).exists():
        raise Http404()

    # For DMs, 'other' is the other person; for groups, this will be None and your template
    # should show thread.name + participants instead (as discussed previously).
    other = thread.participants.exclude(pk=request.user.pk).first()

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            Message.objects.create(
                thread=thread,
                sender=request.user,
                text=form.cleaned_data['text']
            )
            return redirect('messaging:thread', thread_id=thread.id)
    else:
        form = MessageForm()

    messages_qs = thread.messages.select_related('sender')
    page_title = (f"Chat with @{other.username}" if (other and not thread.is_group) 
                  else (thread.name or "Conversation"))

    # Mark as read for the current user (only if there are messages)
    if messages_qs.exists():
        tr, _ = ThreadRead.objects.get_or_create(thread=thread, user=request.user)
        tr.last_read_at = timezone.now()
        tr.save(update_fields=['last_read_at'])

    return render(request, 'messaging/thread.html', {
        'thread': thread,
        'messages': messages_qs,
        'form': form,
        'other': other,
        'title': page_title,
    })
