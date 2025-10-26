from django.urls import path
from . import views

app_name = "messaging"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("compose/<int:user_id>/", views.compose, name="compose"),
    path("t/<int:thread_id>/", views.thread_detail, name="thread"),
    path("users/", views.user_list, name="user_list"),
    path("groups/new/", views.group_new, name="group_new"),   # NEW
]