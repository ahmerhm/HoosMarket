from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404
from django.views.decorators.http import require_POST
from .models import Thread, Message
from .forms import MessageForm

User = get_user_model()

@login_required
def inbox(request):
    threads = (Thread.objects
               .filter(participants=request.user)
               .prefetch_related('participants'))

    rows = []
    for t in threads:
        other = next((p for p in t.participants.all() if p.id != request.user.id), None)
        rows.append({'thread': t, 'other': other})
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

    # See if a thread already exists (do NOT create on GET).
    key = Thread._pair_key_for(request.user.id, other.id)
    thread = Thread.objects.filter(pair_key=key).first()

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            # Ensure the thread exists now; create if needed.
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
        'thread': thread,           # may be None
        'messages': messages_qs,    # empty if thread doesn't exist yet
        'form': form,
        'other': other,
        'title': title,
    })

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

    messages_qs = thread.messages.select_related('sender')
    page_title = f"Chat with @{other.username}" if other else "Conversation"

    return render(request, 'messaging/thread.html', {
        'thread': thread,
        'messages': messages_qs,
        'form': form,
        'other': other,
        'title': page_title,
    })
