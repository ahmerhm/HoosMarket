from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_POST

from django.core.files.base import ContentFile
from pathlib import Path
from io import BytesIO
from PIL import Image
try:
    # Enable Pillow to open HEIC/HEIF if pillow-heif is installed
    from pillow_heif import register_heif_opener  # type: ignore
    register_heif_opener()
except Exception:
    # Safe to ignore if library unavailable locally
    pass


from .models import Profile, Post, PostImages

@login_required
def dashboard(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    role = getattr(profile, "status", "Member")

    posts = Post.objects.all().order_by('-created_at')

    if str(role).lower() == "organizer":
        return render(request, "organizer_dashboard.html", {"profile": profile, "posts": posts})
    else:
        return render(request, "dashboard.html", {"profile": profile, "posts": posts})

@login_required
def profile(request):
    """
    GET: render profile page
    POST: handle inline updates for name or bio from the profile page
          (expects 'action' to be 'update_name' or 'update_bio')
    """
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        # Handle avatar upload (convert HEIC/HEIF to JPEG for browser support)
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

        if action == "update_name":
            full = (request.POST.get("name") or "").strip()
            if full:
                parts = full.split(" ", 1)
                first = parts[0]
                last = parts[1] if len(parts) > 1 else ""
                request.user.first_name = first
                request.user.last_name = last
                request.user.save(update_fields=["first_name", "last_name"])
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

        new_post_obj = Post.objects.create(user = request.user, title = post_title, price = post_price, description = post_description, category=post_category)

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
    role = getattr(profile, "status", "Member")

    if str(role).lower() == "organizer":
        if request.method == "POST":
            post_id = request.POST.get("post_id")
            post = get_object_or_404(Post, id=post_id)
            post.delete()
            return redirect("myposts")
    else:
        if request.method == "POST":
            post_id = request.POST.get("post_id")
            post = get_object_or_404(Post, id=post_id)

            if post.user != request.user:
                return HttpResponseForbidden("You are not the owner of this post")

            post.delete()
            return redirect("myposts")

    return redirect("dashboard")
