from django.urls import path
from .views import assistant_chat, weekly_plan, regenerate_weekly_plan

urlpatterns = [
    path("chat/", assistant_chat, name="assistant-chat"),
    path("weekly-plan/", weekly_plan, name="assistant-weekly-plan"),
    path("weekly-plan/regenerate/", regenerate_weekly_plan, name="assistant-weekly-plan-regenerate"),
]