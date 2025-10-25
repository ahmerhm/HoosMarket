from django.urls import path
from . import views

app_name = "messaging"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("start/", views.start_thread, name="start"),              # (kept)
    path("t/<int:thread_id>/", views.thread_detail, name="thread"),
    path("users/", views.user_list, name="user_list"),             # NEW: popup content
    path("start-with/", views.start_with, name="start_with"),      # NEW: create thread and redirect
]
