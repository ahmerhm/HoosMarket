from django.shortcuts import render, redirect, get_object_or_404
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

from .models import Profile, Post, PostImages


@login_required
def dashboard(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    role = getattr(profile, "status", "Member")

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
      - handle inline updates for nickname or bio from the profile page
        (expects 'action' to be 'update_nickname' or 'update_bio')
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

        if action in ("update_nickname", "update_name"):  # support old action name just in case
            nickname = (request.POST.get("nickname") or request.POST.get("name") or "").strip()
            profile_obj.nickname = nickname
            profile_obj.save(update_fields=["nickname"])
            return redirect("profile")

        elif action == "update_bio":
            profile_obj.bio = request.POST.get("bio") or ""
            profile_obj.save(update_fields=["bio"])
            return redirect("profile")

    return render(
        request,
        "account/profile.html",
        {
            "user": request.user,
            "profile": profile_obj,
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


@login_required
def flag_post(request):
    return redirect("dashboard")
