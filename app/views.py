from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
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

    if str(role).lower() == "organizer":
        return render(request, "organizer_dashboard.html", {"profile": profile, "posts": posts})
    else:
        return render(request, "dashboard.html", {"profile": profile, "posts": posts})


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
        post_images = request.FILES.getlist("images")

        new_post_obj = Post.objects.create(
            user=request.user,
            title=post_title,
            price=post_price,
            description=post_description,
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
