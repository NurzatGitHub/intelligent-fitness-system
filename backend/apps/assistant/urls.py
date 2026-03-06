from django.urls import path
from .views import assistant_chat

urlpatterns = [
    path("chat/", assistant_chat, name="assistant-chat"),
]