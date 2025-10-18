from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Profile

@login_required
def dashboard(request):
    # ensure a Profile exists for this user
    profile, _ = Profile.objects.get_or_create(user=request.user)

    # get the role safely (default to member if not set)
    role = getattr(profile, "status", "Member")  # or profile.role if you have that field

    if role.lower() == "organizer":
        return render(request, "organizer_dashboard.html", {"profile": profile})
    else:
        return render(request, "dashboard.html", {"profile": profile})

@login_required
def profile(request):
    return render(request, "account/profile.html", {"user": request.user})