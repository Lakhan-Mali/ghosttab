"""Forms used by project views."""
from django import forms
from urllib.parse import urlparse

from .models import Project, SavedPage


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("title", "goal", "status")
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Project title"}),
            "goal": forms.Textarea(attrs={"rows": 3, "placeholder": "What are you trying to accomplish?"}),
        }


class SavedPageForm(forms.ModelForm):
    class Meta:
        model = SavedPage
        fields = ("url", "title", "note", "raw_text")
        widgets = {
            "url": forms.URLInput(attrs={"placeholder": "https://example.com/article"}),
            "title": forms.TextInput(attrs={"placeholder": "Page title (optional)"}),
            "note": forms.Textarea(attrs={"rows": 2, "placeholder": "Why did you save this?"}),
            "raw_text": forms.Textarea(attrs={"rows": 4, "placeholder": "Paste relevant text from the page (optional)"}),
        }

    def clean_url(self):
        url = self.cleaned_data["url"].strip()
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise forms.ValidationError("URL must use http or https.")
        if not parsed.netloc:
            raise forms.ValidationError("URL must include a domain.")
        return url


class QuickAddURLForm(forms.Form):
    url = forms.URLField(widget=forms.URLInput(attrs={"placeholder": "Paste a URL to add to a project"}))
    project_id = forms.IntegerField(required=False, widget=forms.HiddenInput)


class BulkImportURLsForm(forms.Form):
    """Multi-line URL paste, one per line."""
    urls = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 6, "placeholder": "https://...\nhttps://..."}),
        help_text="One URL per line.",
    )
    project_id = forms.IntegerField(required=False, widget=forms.HiddenInput)

    def clean_urls(self):
        raw = self.cleaned_data["urls"]
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        bad = [ln for ln in lines if not ln.lower().startswith(("http://", "https://"))]
        if bad:
            raise forms.ValidationError(f"Each line must be a full URL. Bad: {bad[:3]}")
        return lines
