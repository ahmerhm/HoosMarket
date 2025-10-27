from django.contrib import admin
from .models import Profile
from messaging.models import Message

# Register your models here.
admin.site.register(Profile)
admin.site.register(Message)