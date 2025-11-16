from django.contrib import auth
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

class CheckSuspension:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_staff:
            try:
                suspended_url = reverse('suspended_page')
            except:
                suspended_url = '/suspended'
            if request.path == suspended_url:
                return self.get_response(request)
        
            if hasattr(request.user, 'profile') and request.user.profile.status == "Suspended":
                messages.error(request, 
                        "Your account has been suspended by an administrator. "
                        "Please contact support if you believe this is an error."
                    )
                auth.logout(request)

                return redirect(suspended_url)
        
        response = self.get_response(request)
        return response