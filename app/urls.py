"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include
from . import views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

def root(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    else:
        return redirect("account_login")

urlpatterns = [
    path("admin/", admin.site.urls, name="admin_login"),
    path("", root),
    path("accounts/", include("allauth.urls")),
    path("dashboard/",views.dashboard, name="dashboard"),
    path("myaccount/", views.profile, name="profile"),
    path("messages/", include(("messaging.urls", "messaging"), namespace="messaging")),
    path("newpost/", views.new_post, name="newpost"),
    path("delete-account/", views.delete_account, name="delete_account"),
    path("myposts/", views.my_posts, name="myposts"),
    path("deletepost/", views.delete_post, name="delete_post")
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root = settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)