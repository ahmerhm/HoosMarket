from django.shortcuts import render

def dashboard(request):
    context = {
        "title": "Website!",
        "message": "Dashboard page"
    }
    return render(request, "dashboard.html", context)
