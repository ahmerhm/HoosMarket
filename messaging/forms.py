from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class UserChoiceField(forms.ModelMultipleChoiceField):
    """
    Show each user using:
      - @nickname if profile.nickname is set
      - full name if available
      - @username as a final fallback
    """
    def label_from_instance(self, obj):
        profile = getattr(obj, "profile", None)
        nick = getattr(profile, "nickname", "") if profile else ""
        full = obj.get_full_name()

        if nick:
            return f"@{nick}"
        elif full:
            return full
        return f"@{obj.username}"


class GroupCreateForm(forms.Form):
    name = forms.CharField(max_length=120, label="Group name")
    members = UserChoiceField(
        queryset=User.objects.none(), 
        required=True,
        widget=forms.CheckboxSelectMultiple,
        label="Add members",
    )

    def __init__(self, *args, **kwargs):
        me = kwargs.pop("me", None)
        super().__init__(*args, **kwargs)

        qs = User.objects.all()
        if me is not None:
            qs = qs.exclude(pk=me.pk)

        self.fields["members"].queryset = qs.order_by("username")


class StartThreadForm(forms.Form):
    username = forms.CharField(label="Send a message to (username)")


class MessageForm(forms.Form):
    text = forms.CharField(widget=forms.Textarea(attrs={
        "rows": 3,
        "placeholder": "Write a message..."
    }))
