from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages as django_messages

from .models import Thread, Message, ThreadRead
from .models import MessageFlag
from .forms import MessageForm, GroupCreateForm  
from app.models import Profile

User = get_user_model()


def _display_name(user):
    """
    Prefer:
    1) profile.nickname (if present)
    2) user.get_full_name()
    3) user.username
    """
    profile = getattr(user, "profile", None)
    nick = getattr(profile, "nickname", "") if profile else ""
    full = user.get_full_name()

    if nick:
        return nick
    if full:
        return full
    return user.username


@login_required
def inbox(request):
    threads = (
        Thread.objects
        .filter(participants=request.user)
        .prefetch_related(
            'participants__profile',
            'participants',
            'messages__sender__profile',
            'messages__sender',
            'messages',
        )
    )

    rows = []
    for t in threads:
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
    users = (
        User.objects
        .exclude(pk=request.user.pk)
        .select_related("profile")
        .order_by("username")
    )
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

    messages_qs = (
        thread.messages
        .select_related('sender', 'sender__profile')
        if thread else []
    )

    display = _display_name(other)
    title = f"Chat with {display}"

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

    messages_qs = thread.messages.select_related('sender', 'sender__profile')

    if other and not thread.is_group:
        display = _display_name(other)
        page_title = f"Chat with {display}"
    else:
        page_title = thread.name or "Conversation"

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

@login_required
@require_POST
def flag_message(request, message_id):
    """
    Regular users (participants in the thread) can flag a specific message.
    """
    message = get_object_or_404(
        Message.objects.select_related("thread", "sender"),
        pk=message_id,
    )

    # Only participants in the thread can flag
    if not message.thread.participants.filter(pk=request.user.pk).exists():
        raise Http404()

    # Don't let users flag their own messages (optional, mirroring posts)
    if message.sender_id == request.user.id:
        return redirect("messaging:thread", thread_id=message.thread_id)

    existing = MessageFlag.objects.filter(
        message=message,
        flagged_by=request.user,
        resolved=False,
    )
    if existing.exists():
        return redirect("messaging:thread", thread_id=message.thread_id)

    reason = (request.POST.get("reason") or "User flagged this message").strip()
    MessageFlag.objects.create(
        message=message,
        flagged_by=request.user,
        reason=reason,
    )
    return redirect("messaging:thread", thread_id=message.thread_id)


@staff_member_required
def admin_edit_message(request, message_id):
    """
    Admin view to edit the text of a message.
    """
    message = get_object_or_404(
        Message.objects.select_related("thread", "sender"),
        pk=message_id,
    )

    if request.method == "POST":
        new_text = (request.POST.get("text") or "").strip()
        if not new_text:
            django_messages.error(request, "Message text cannot be empty.")
        else:
            message.text = new_text
            message.save(update_fields=["text"])
            django_messages.success(request, "Message updated successfully.")
            return redirect("admin_dashboard")

    return render(request, "admin/edit_message.html", {"message": message})


@staff_member_required
def admin_delete_message(request, message_id):
    """
    Admin view to delete a message.
    """
    message = get_object_or_404(Message, pk=message_id)
    message.delete()
    django_messages.success(request, "Message deleted.")
    return redirect("admin_dashboard")


@staff_member_required
def admin_resolve_message_flag(request, flag_id):
    """
    Mark a MessageFlag as resolved.
    """
    flag = get_object_or_404(MessageFlag, pk=flag_id)
    flag.resolved = True
    flag.save(update_fields=["resolved"])
    django_messages.success(request, "Message flag marked as resolved.")
    return redirect("admin_dashboard")
