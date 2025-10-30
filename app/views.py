from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Profile

@login_required
def dashboard(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    role = getattr(profile, "status", "Member")

    if str(role).lower() == "organizer":
        return render(request, "organizer_dashboard.html", {"profile": profile})
    else:
        return render(request, "dashboard.html", {"profile": profile})

@login_required
def profile(request):
    """
    GET: render profile page
    POST: handle inline updates for name or bio from the profile page
          (expects 'action' to be 'update_name' or 'update_bio')
    """
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        # if uploaded image 
        if "image" in request.FILES:
            profile_obj.avatar = request.FILES["image"]
            profile_obj.save(update_fields=["avatar"])
            return redirect("profile")
        # if name updated
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

        #bio changes 
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
    return render(request, 'post/new_post.html')