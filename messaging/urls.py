from django.urls import path
from . import views

app_name = "messaging"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("compose/<int:user_id>/", views.compose, name="compose"),
    path("t/<int:thread_id>/", views.thread_detail, name="thread"),
    path("users/", views.user_list, name="user_list"),
    path("groups/new/", views.group_new, name="group_new"),

    path("m/<int:message_id>/flag/", views.flag_message, name="flag_message"),
    path("m/<int:message_id>/edit/", views.admin_edit_message, name="admin_edit_message"),
    path("m/<int:message_id>/delete/", views.admin_delete_message, name="admin_delete_message"),
    path("flags/<int:flag_id>/resolve/", views.admin_resolve_message_flag, name="admin_resolve_message_flag"),
]
