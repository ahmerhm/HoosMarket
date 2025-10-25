from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404
from .models import Thread, Message
from .forms import StartThreadForm, MessageForm
from django.views.decorators.http import require_POST

User = get_user_model()

@login_required
def inbox(request):
    threads = (Thread.objects
               .filter(participants=request.user)
               .prefetch_related('participants', 'messages'))
    return render(request, 'messaging/inbox.html', {'threads': threads, 'title': 'Messages'})

@login_required
def start_thread(request):
    if request.method == 'POST':
        form = StartThreadForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            other = get_object_or_404(User, username=username)
            thread, _created = Thread.for_users(request.user, other)
            return redirect('messaging:thread', thread_id=thread.id)
    else:
        form = StartThreadForm()
    return render(request, 'messaging/start.html', {'form': form, 'title': 'New Message'})

@login_required
def thread_detail(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
    if not thread.participants.filter(pk=request.user.pk).exists():
        raise Http404()

    # find the other user in this 1:1 thread
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

    # nice page title like: "Chat with @alice"
    page_title = f"Chat with @{other.username}" if other else "Conversation"

    return render(
        request,
        'messaging/thread.html',
        {
            'thread': thread,
            'messages': messages_qs,
            'form': form,
            'other': other,                 # <-- pass single other user
            'title': page_title,            # <-- better <title>
        }
    )


User = get_user_model()

@login_required
def user_list(request):
    """
    Renders a partial with all users (except me), optionally filtered by ?q=.
    This HTML is loaded into the modal via fetch().
    """
    q = request.GET.get("q", "").strip()
    users = User.objects.exclude(pk=request.user.pk).order_by("username")
    if q:
        users = users.filter(username__icontains=q)
    return render(request, "messaging/_user_list.html", {"users": users, "q": q})

@login_required
@require_POST
def start_with(request):
    """
    Creates (or finds) a 1:1 thread with the selected user_id and redirects to it.
    """
    user_id = request.POST.get("user_id")
    other = get_object_or_404(User, pk=user_id)
    thread, _ = Thread.for_users(request.user, other)
    return redirect("messaging:thread", thread_id=thread.id)
