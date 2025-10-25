from django.urls import path
from . import views

app_name = "messaging"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("start/", views.start_thread, name="start"),
    path("t/<int:thread_id>/", views.thread_detail, name="thread"),
]
