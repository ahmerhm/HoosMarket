from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.core.files.base import ContentFile
from django.conf import settings
from pathlib import Path
from io import BytesIO
from PIL import Image
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib import messages

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:
    pass

from .models import Profile, Post, PostImages, PostFlag
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from messaging.models import Message, MessageFlag

User = get_user_model()


def admin_only(view_func):
    """Decorator for views that only staff (admins) can access."""
    return staff_member_required(view_func)


def is_moderator_email(email: str) -> bool:
    """
    Check whether an email is in the MODERATOR_EMAILS from settings.

    Handles both:
    - MODERATOR_EMAILS = "a@x.com, b@y.com"   (string)
    - MODERATOR_EMAILS = ["a@x.com", "b@y.com"] (list/tuple)
    """
    if not email:
        return False

    raw = getattr(settings, "MODERATOR_EMAILS", [])

    if isinstance(raw, str):
        allowed = [e.strip().lower() for e in raw.split(",") if e.strip()]
    else:
        allowed = [str(e).strip().lower() for e in raw]

    print("DEBUG MODERATOR_EMAILS:", allowed, "| checking:", email)

    return email.strip().lower() in allowed



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

    if getattr(profile_obj, "onboarding_complete", False):
        return redirect("dashboard")

    if request.method == "POST":
        interests = request.POST.getlist("interests")
        nickname = (request.POST.get("nickname") or "").strip()
        bio = request.POST.get("bio") or ""

        max_len = Profile._meta.get_field("nickname").max_length or 64
        if nickname:
            nickname = nickname[:max_len]

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

        profile_obj.sustainability_interests = interests

        if nickname:
            profile_obj.nickname = nickname
        if bio:
            profile_obj.bio = bio

        profile_obj.onboarding_complete = True
        profile_obj.save()
        return redirect("dashboard")

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

    if not getattr(profile, "onboarding_complete", False):
        return redirect("onboarding")

    posts = Post.objects.all().order_by('-created_at')
    posts = posts.exclude(hidden_from=request.user)

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
            max_len = Profile._meta.get_field("nickname").max_length or 64
            if nickname:
                nickname = nickname[:max_len]
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

        hidden_from_ids = request.POST.getlist("hidden_from")

        new_post_obj = Post.objects.create(
            user=request.user,
            title=post_title,
            price=post_price,
            description=post_description,
            category=post_category,
        )

        if hidden_from_ids:
            users_to_hide = User.objects.filter(id__in=hidden_from_ids)
            new_post_obj.hidden_from.set(users_to_hide)

        for image in post_images:
            PostImages.objects.create(post=new_post_obj, image=image)

        return redirect("dashboard")

    users = User.objects.exclude(id=request.user.id)
    return render(request, 'post/new_post.html', {"users": users})


@login_required
@require_POST
def delete_account(request):
    user = request.user
    EmailAddress.objects.filter(user=user).delete()
    SocialAccount.objects.filter(user=user).delete()
    user.delete()
    messages.success(request, "Your account has been deleted.")
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


@login_required
def post_login_redirect(request):
    """
    After any successful login:

    - If the user's email is in MODERATOR_EMAILS, mark them as staff (admin).
    - If not, and they are staff (but not superuser), demote them back.
    - Then send everyone to the regular dashboard.
    Admin powers are controlled purely by user.is_staff.
    """
    user = request.user
    is_mod = is_moderator_email(user.email)

    if is_mod and not user.is_staff:
        user.is_staff = True
        user.save(update_fields=["is_staff"])
    elif not is_mod and user.is_staff and not user.is_superuser:
        user.is_staff = False
        user.save(update_fields=["is_staff"])

    return redirect("dashboard")



@login_required
def flag_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if post.user == request.user:
        return redirect("dashboard")

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
def admin_delete_post(request, post_id):
    """
    Admins can delete any post from the admin panel.
    """
    post = get_object_or_404(Post, id=post_id)
    post.delete()
    return redirect("admin_dashboard")


@admin_only
def admin_suspend_user(request, user_id):
    """
    Admins can suspend a user. This sets profile.status = 'Suspended'.
    """
    profile = get_object_or_404(Profile, user__id=user_id)
    profile.status = "Suspended"
    profile.save()
    return redirect("admin_dashboard")


@admin_only
def admin_restore_user(request, user_id):
    """
    Admins can restore a suspended user back to 'Member' status.
    """
    profile = get_object_or_404(Profile, user__id=user_id)
    profile.status = "Member"
    profile.save()
    return redirect("admin_dashboard")


@admin_only
def admin_edit_post(request, post_id):
    """
    Admin can edit a post's title and description.
    Used especially for flagged posts, but works for any post.
    """
    post = get_object_or_404(Post, id=post_id)

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        description = request.POST.get("description") or ""

        if not title:
            messages.error(request, "Title is required.")
        else:
            post.title = title
            post.description = description
            post.save(update_fields=["title", "description"])
            messages.success(request, "Post updated successfully.")
            return redirect("admin_dashboard")

    return render(request, "admin/edit_post.html", {"post": post})


@admin_only
def admin_resolve_flag(request, flag_id):
    """
    Mark all unresolved flags for the same post as resolved.
    (Called with any single flag_id from that post.)
    """
    flag = get_object_or_404(PostFlag, id=flag_id)
    PostFlag.objects.filter(post=flag.post, resolved=False).update(resolved=True)
    messages.success(request, "All flags for this post have been marked as resolved.")
    return redirect("admin_dashboard")


@admin_only
def admin_flag_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    existing = PostFlag.objects.filter(post=post, flagged_by=request.user, resolved=False)
    if existing.exists():
        return redirect("admin_dashboard")

    PostFlag.objects.create(
        post=post,
        flagged_by=request.user,
        reason="Flagged by admin"
    )
    return redirect("admin_dashboard")

@admin_only
def admin_edit_message(request, message_id):
    """
    Admin can edit the text of a flagged (or any) message.
    """
    message = get_object_or_404(Message, id=message_id)

    if request.method == "POST":
        text = (request.POST.get("text") or "").strip()
        if not text:
            messages.error(request, "Message text cannot be empty.")
        else:
            message.text = text
            message.save(update_fields=["text"])
            messages.success(request, "Message updated successfully.")
            return redirect("admin_dashboard")

    return render(request, "admin/edit_message.html", {"message": message})

@admin_only
def admin_delete_message(request, message_id):
    """
    Admins can delete a message from the admin panel.
    """
    message = get_object_or_404(Message, id=message_id)
    message.delete()
    messages.success(request, "Message deleted.")
    return redirect("admin_dashboard")

@admin_only
def admin_resolve_message_flag(request, flag_id):
    """
    Mark a message flag as resolved (message may still remain).
    """
    flag = get_object_or_404(MessageFlag, id=flag_id)
    flag.resolved = True
    flag.save(update_fields=["resolved"])
    messages.success(request, "Message flag has been marked as resolved.")
    return redirect("admin_dashboard")

def is_admin(user):
    return user.is_staff or user.is_superuser


@admin_only
def admin_dashboard(request):
    posts = Post.objects.all().order_by("-created_at")

    flagged_posts_qs = (
        Post.objects
        .filter(flags__resolved=False)
        .distinct()
        .prefetch_related(
            "images",
            "flags__flagged_by__profile",
            "user__profile",
        )
        .order_by("-flags__created_at")
    )

    flagged_posts_list = []
    for post in flagged_posts_qs:
        unresolved_flags = [f for f in post.flags.all() if not f.resolved]
        if not unresolved_flags:
            continue

        flaggers = []
        seen = set()
        for f in unresolved_flags:
            u = f.flagged_by
            display = getattr(getattr(u, "profile", None), "display_name", None) or u.username
            if display not in seen:
                seen.add(display)
                flaggers.append(display)

        latest_flag = max(unresolved_flags, key=lambda f: f.created_at)

        flagged_posts_list.append({
            "post": post,
            "flaggers": flaggers,
            "reason": latest_flag.reason,
            "latest_flag": latest_flag,
            "first_flag_id": unresolved_flags[0].id,  
        })
    unresolved_message_flags = (
        MessageFlag.objects
        .filter(resolved=False)
        .select_related(
            "message",
            "message__sender",
            "message__thread",
            "flagged_by",
        )
        .order_by("-created_at")
    )

    total_users = User.objects.count()
    suspended_users = User.objects.filter(profile__status="Suspended").count()
    total_posts = Post.objects.count()
    flagged_posts_count = len(flagged_posts_list)
    flagged_message_count = unresolved_message_flags.count()

    suspended_user_list = User.objects.filter(profile__status="Suspended")

    return render(request, "admin/admin_dashboard.html", {
        "posts": posts,
        "flagged_posts_list": flagged_posts_list,
        "message_flags": unresolved_message_flags,
        "total_users": total_users,
        "suspended_users": suspended_users,
        "total_posts": total_posts,
        "flagged_posts": flagged_posts_count,
        "flagged_message_count": flagged_message_count,
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
