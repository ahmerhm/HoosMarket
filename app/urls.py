from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

from . import views   # <-- single import from views


def root(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("account_login")


urlpatterns = [
    # --- REAL Django admin ---
    path("admin/", admin.site.urls),

    # --- Custom Admin Dashboard (your admin panel) ---
    # Accessed only by staff users; visible via "Review Content" link in the navbar.
    path("admin-panel/", views.admin_dashboard, name="admin_dashboard"),

    path(
        "admin-panel/delete-post/<int:post_id>/",
        views.admin_delete_post,
        name="admin_delete_post",
    ),
    path(
        "admin-panel/suspend-user/<int:user_id>/",
        views.admin_suspend_user,
        name="admin_suspend_user",
    ),
    path(
        "admin-panel/restore-user/<int:user_id>/",
        views.admin_restore_user,
        name="admin_restore_user",
    ),

    # Root -> dashboard or login
    path("", root),

    # Allauth (login, signup, etc.)
    path("accounts/", include("allauth.urls")),

    # Main app views
    path("dashboard/", views.dashboard, name="dashboard"),
    path("setup/", views.onboarding, name="onboarding"),
    path("myaccount/", views.profile, name="profile"),
    path("messages/", include(("messaging.urls", "messaging"), namespace="messaging")),
    path("newpost/", views.new_post, name="newpost"),
    path("delete-account/", views.delete_account, name="delete_account"),
    path("myposts/", views.my_posts, name="myposts"),
    path("deletepost/", views.delete_post, name="delete_post"),
    path("flagpost/<int:post_id>/", views.flag_post, name="flag_post"),

    path(
        "admin-panel/resolve-flag/<int:flag_id>/",
        views.admin_resolve_flag,
        name="admin_resolve_flag",
    ),
    path(
        "admin-panel/flag-post/<int:post_id>/",
        views.admin_flag_post,
        name="admin_flag_post",
    ),

    # Logout
    path(
        "logout/",
        auth_views.LogoutView.as_view(
            template_name="account/logout.html",
            next_page="account_login",
        ),
        name="logout",
    ),

    # After login: promote moderators to staff & send to dashboard
    path("after-login/", views.post_login_redirect, name="post_login_redirect"),

    # Suspended user page
    path("suspended/", views.suspended_page_view, name="suspended_page"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
