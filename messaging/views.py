from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404
from .models import Thread, Message
from .forms import StartThreadForm, MessageForm

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
    # Permission check: must be a participant
    if not thread.participants.filter(pk=request.user.pk).exists():
        raise Http404()

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
    other_users = thread.participants.exclude(pk=request.user.pk)
    return render(
        request, 'messaging/thread.html',
        {'thread': thread, 'messages': messages_qs, 'form': form,
         'other_users': other_users, 'title': 'Conversation'}
    )
