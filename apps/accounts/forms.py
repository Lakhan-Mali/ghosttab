"""Account forms: signup, login, settings."""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import UserProfile

User = get_user_model()


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    display_name = forms.CharField(required=False, max_length=120)

    class Meta:
        model = User
        fields = ("email", "display_name")

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with that email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.display_name = self.cleaned_data.get("display_name", "")
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))


class ProfileSettingsForm(forms.ModelForm):
    display_name = forms.CharField(required=False, max_length=120)

    class Meta:
        model = UserProfile
        fields = ("theme", "reduced_motion", "send_product_updates",
                  "auto_group_new_pages", "auto_generate_actions")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields["display_name"].initial = self.user.display_name

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            self.user.display_name = self.cleaned_data.get("display_name", "")
            self.user.save()
        if commit:
            profile.save()
        return profile
