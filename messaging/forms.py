from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


def display_name(user):
    """
    Prefer:
    1) profile.nickname
    2) user.get_full_name()  (Google name)
    3) user.username
    (No @ anywhere.)
    """
    profile = getattr(user, "profile", None)
    nick = getattr(profile, "nickname", "") if profile else ""
    full = user.get_full_name()

    if nick:
        return nick
    if full:
        return full
    return user.username


class GroupCreateForm(forms.Form):
    name = forms.CharField(
        max_length=120,
        label="Group name",
        widget=forms.TextInput(attrs={
            "placeholder": "Group name",
        }),
    )
    members = forms.ModelMultipleChoiceField(
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

        qs = qs.select_related("profile").order_by("username")
        self.fields["members"].queryset = qs

        self.fields["members"].label_from_instance = display_name


class StartThreadForm(forms.Form):
    username = forms.CharField(label="Send a message to (username)")


class MessageForm(forms.Form):
    text = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Write a message...",
            }
        )
    )
