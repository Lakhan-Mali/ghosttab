from django.urls import path
from . import views

urlpatterns = [
    path("", views.action_queue, name="action_queue"),
]
