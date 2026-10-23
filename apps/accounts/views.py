"""Account views: signup, login, logout, settings."""
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from .forms import SignupForm, LoginForm, ProfileSettingsForm

User = get_user_model()


@require_http_methods(["GET", "POST"])
def signup_view(request):
    if request.user.is_authenticated:
        return redirect("/app/")
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome to GhostTab AI. Your workspace is ready.")
            return redirect("/app/?welcome=1")
    else:
        form = SignupForm()
    return render(request, "accounts/signup.html", {"form": form, "active_nav": "signup"})


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("/app/")
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower().strip()
            password = form.cleaned_data["password"]
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get("next") or "/app/"
                return redirect(next_url)
            else:
                form.add_error(None, "Email or password is incorrect.")
    else:
        form = LoginForm()
    return render(request, "accounts/login.html", {"form": form, "active_nav": "login"})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("/")


@login_required
@require_http_methods(["GET", "POST"])
def settings_view(request):
    profile = request.user.profile
    if request.method == "POST":
        form = ProfileSettingsForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings saved.")
            return redirect("settings")
    else:
        form = ProfileSettingsForm(instance=profile, user=request.user)
    return render(request, "accounts/settings.html", {"form": form, "active_nav": "settings"})
