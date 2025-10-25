from django import forms

class StartThreadForm(forms.Form):
    username = forms.CharField(label="Send a message to (username)")

class MessageForm(forms.Form):
    text = forms.CharField(widget=forms.Textarea(attrs={
        "rows": 3, "placeholder": "Write a message..."
    }))
