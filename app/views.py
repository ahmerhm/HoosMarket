from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.core.files.base import ContentFile
from pathlib import Path
from io import BytesIO
from PIL import Image
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:
    pass

from .models import Profile, Post, PostImages, PostFlag
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from .models import *
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
User = get_user_model()
# ------- admin-only decorator -------
def admin_only(view_func):
    return staff_member_required(view_func)
# ---- Sustainability interests master list ----
SUSTAINABILITY_CHOICES = [
    ("zero_waste", "Zero-waste & circular economy"),
    ("food", "Sustainable food & agriculture"),
    ("energy", "Energy & climate"),
    ("transport", "Low-carbon transport & mobility"),
    ("community", "Community events & volunteering"),
    ("advocacy", "Advocacy, education & policy"),
]


@login_required
def onboarding(request):
    """
    First-time setup:
    - Pick sustainability interests
    - (Optional) nickname + bio
    - Confirm community norms
    Runs only once per user (gated by profile.onboarding_complete).
    """
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)

    # If they've already completed onboarding, don't show again
    if getattr(profile_obj, "onboarding_complete", False):
        return redirect("dashboard")

    if request.method == "POST":
        interests = request.POST.getlist("interests")
        nickname = (request.POST.get("nickname") or "").strip()
        bio = request.POST.get("bio") or ""

        # Norms checkbox must be ticked
        if request.POST.get("accept_norms") != "on":
            return render(
                request,
                "account/onboarding.html",
                {
                    "user": request.user,
                    "profile": profile_obj,
                    "SUSTAINABILITY_CHOICES": SUSTAINABILITY_CHOICES,
                    "error": "Please review and accept the community norms to continue.",
                    "selected_interests": interests,
                    "nickname": nickname,
                    "bio": bio,
                },
            )

        # Save interests
        profile_obj.sustainability_interests = interests

        # Optional nickname + bio
        if nickname:
            profile_obj.nickname = nickname
        if bio:
            profile_obj.bio = bio

        profile_obj.onboarding_complete = True
        profile_obj.save()
        return redirect("dashboard")

    # GET
    return render(
        request,
        "account/onboarding.html",
        {
            "user": request.user,
            "profile": profile_obj,
            "SUSTAINABILITY_CHOICES": SUSTAINABILITY_CHOICES,
            "selected_interests": getattr(profile_obj, "sustainability_interests", []) or [],
        },
    )


@login_required
def dashboard(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    role = getattr(profile, "status", "Member")

    # If they haven't done first-time setup yet, send them there
    if not getattr(profile, "onboarding_complete", False):
        return redirect("onboarding")

    posts = Post.objects.all().order_by('-created_at')
    categories = Post._meta.get_field('category').choices

    selected_category = request.GET.get('category') or None
    search_query = (request.GET.get('q') or "").strip()

    if selected_category:
        posts = posts.filter(category=selected_category)

    if search_query:
        posts = posts.filter(title__icontains=search_query)

    context = {
        "profile": profile,
        "posts": posts,
        "selected_category": selected_category,
        "categories": categories,
        "search_query": search_query,
    }

    if str(role).lower() == "organizer":
        return render(request, "organizer_dashboard.html", context)
    else:
        return render(request, "dashboard.html", context)


@login_required
def profile(request):
    """
    GET: render profile page
    POST:
      - handle avatar upload
      - handle inline updates for nickname or bio
      - handle updates for sustainability interests
    """
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        # Avatar upload
        if "image" in request.FILES:
            uploaded = request.FILES["image"]
            name = getattr(uploaded, "name", "avatar")
            content_type = getattr(uploaded, "content_type", "")
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""

            if ext in {"heic", "heif"} or content_type in {"image/heic", "image/heif"}:
                try:
                    img = Image.open(uploaded)
                    if img.mode not in ("RGB", "L"):
                        img = img.convert("RGB")
                    buf = BytesIO()
                    img.save(buf, format="JPEG", quality=90)
                    buf.seek(0)
                    new_name = f"{Path(name).stem}.jpg"
                    profile_obj.avatar.save(new_name, ContentFile(buf.read()), save=True)
                except Exception:
                    profile_obj.avatar = uploaded
                    profile_obj.save(update_fields=["avatar"])
            else:
                profile_obj.avatar = uploaded
                profile_obj.save(update_fields=["avatar"])
            return redirect("profile")

        action = (request.POST.get("action") or "").strip()

        if action in ("update_nickname", "update_name"):
            nickname = (request.POST.get("nickname") or request.POST.get("name") or "").strip()
            profile_obj.nickname = nickname
            profile_obj.save(update_fields=["nickname"])
            return redirect("profile")

        elif action == "update_bio":
            profile_obj.bio = request.POST.get("bio") or ""
            profile_obj.save(update_fields=["bio"])
            return redirect("profile")

        elif action == "update_interests":
            interests = request.POST.getlist("interests")
            profile_obj.sustainability_interests = interests
            profile_obj.save(update_fields=["sustainability_interests"])
            return redirect("profile")

    return render(
        request,
        "account/profile.html",
        {
            "user": request.user,
            "profile": profile_obj,
            "SUSTAINABILITY_CHOICES": SUSTAINABILITY_CHOICES,
        },
    )


@login_required
def new_post(request):
    if request.method == "POST":
        post_title = request.POST.get("title")
        post_price = request.POST.get("price")
        post_description = request.POST.get("description")
        post_category = request.POST.get("category")
        post_images = request.FILES.getlist("images")

        new_post_obj = Post.objects.create(
            user=request.user,
            title=post_title,
            price=post_price,
            description=post_description,
            category=post_category,
        )

        for image in post_images:
            PostImages.objects.create(post=new_post_obj, image=image)

        return redirect("dashboard")

    return render(request, 'post/new_post.html')


@login_required
@require_POST
def delete_account(request):
    from django.contrib.auth import logout
    user = request.user
    logout(request)
    user.delete()
    return redirect("account_login")


@login_required
def my_posts(request):
    posts = Post.objects.filter(user=request.user).order_by('-created_at')
    return render(request, "post/my_posts.html", {"posts": posts})


@login_required
def delete_post(request):
    """
    Organizers can delete any post.
    Regular users can only delete their own posts.
    """
    profile, _ = Profile.objects.get_or_create(user=request.user)
    role = getattr(profile, "status", "Member")

    if request.method == "POST":
        post_id = request.POST.get("post_id")
        post = get_object_or_404(Post, id=post_id)

        if str(role).lower() != "organizer" and post.user != request.user:
            return HttpResponseForbidden("You are not the owner of this post")

        post.delete()
        return redirect("myposts")

    return redirect("dashboard")

@admin_only
def admin_delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    post.delete()
    return redirect("admin_dashboard")  # fixed


@admin_only
def admin_suspend_user(request, user_id):
    profile = get_object_or_404(Profile, user__id=user_id)
    profile.status = "Suspended"
    profile.save()
    return redirect("admin_dashboard")  # fixed


@admin_only
def admin_restore_user(request, user_id):
    profile = get_object_or_404(Profile, user__id=user_id)
    profile.status = "Member"
    profile.save()
    return redirect("admin_dashboard")  # fixed


@login_required
def post_login_redirect(request):
    """
    Redirect AFTER login:
    - staff users → custom admin dashboard
    - regular users → dashboard
    """
    if request.user.is_staff:
        return redirect("admin_dashboard")
    return redirect("dashboard")

@login_required
def flag_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    # Prevent flagging your own post
    if post.user == request.user:
        return redirect("dashboard")

    # Prevent duplicate flags
    existing = PostFlag.objects.filter(post=post, flagged_by=request.user, resolved=False)
    if existing.exists():
        return redirect("dashboard")

    PostFlag.objects.create(
        post=post,
        flagged_by=request.user,
        reason="User flagged this post"
    )
    return redirect("dashboard")

@admin_only
def admin_resolve_flag(request, flag_id):
    flag = get_object_or_404(PostFlag, id=flag_id)
    flag.resolved = True
    flag.save()
    return redirect("admin_dashboard")

@admin_only
def admin_flag_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    # Prevent duplicate flags by admin
    existing = PostFlag.objects.filter(post=post, flagged_by=request.user, resolved=False)
    if existing.exists():
        return redirect("admin_dashboard")

    PostFlag.objects.create(
        post=post,
        flagged_by=request.user,
        reason="Flagged by admin"
    )
    return redirect("admin_dashboard")


def is_admin(user):
    return user.is_staff or user.is_superuser

@staff_member_required
def admin_profile(request):
    user = request.user
    return render(request, "admin/admin_profile.html", {
        "user": user,
    })

def admin_dashboard(request):

    # --- All posts ---
    posts = Post.objects.all().order_by("-created_at")

    # --- Flagged posts ---
    flags = PostFlag.objects.select_related("post", "flagged_by").order_by("-created_at")

    # --- Stats ---
    total_users = User.objects.count()
    suspended_users = User.objects.filter(profile__status="Suspended").count()
    total_posts = Post.objects.count()
    flagged_posts = flags.count()

    # --- Suspended user list (for your new section) ---
    suspended_user_list = User.objects.filter(profile__status="Suspended")

    return render(request, "admin/admin_dashboard.html", {
        "posts": posts,
        "flags": flags,
        "total_users": total_users,
        "suspended_users": suspended_users,
        "total_posts": total_posts,
        "flagged_posts": flagged_posts,
        "suspended_user_list": suspended_user_list,
    })

def suspended_page_view(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile') and request.user.profile.status == "Suspended":
            auth.logout(request)
            return render(request, 'suspended.html')
        else:
            return redirect('dashboard')
    return render(request, 'suspended.html')
