# messaging/forms.py
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class GroupCreateForm(forms.Form):
    name = forms.CharField(max_length=120, label="Group name")
    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),  # set in __init__
        required=True,
        widget=forms.CheckboxSelectMultiple,
        label="Add members"
    )

    def __init__(self, *args, **kwargs):
        me = kwargs.pop("me")
        super().__init__(*args, **kwargs)
        self.fields["members"].queryset = User.objects.exclude(pk=me.pk).order_by("username")

class StartThreadForm(forms.Form):
    username = forms.CharField(label="Send a message to (username)")

class MessageForm(forms.Form):
    text = forms.CharField(widget=forms.Textarea(attrs={
        "rows": 3, "placeholder": "Write a message..."
    }))
