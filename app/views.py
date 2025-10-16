from django.shortcuts import render

def about(request):
    context = {
        "title": "Website!",
        "message": "Dashboard page"
    }
    return render(request, "about.html", context)
