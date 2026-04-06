from django.urls import path
from .views import create_workout_session, workout_history, workout_stats

urlpatterns = [
    path("sessions/", create_workout_session, name="workout-session-create"),
    path("history/", workout_history, name="workout-history"),
    path("stats/", workout_stats, name="workout-stats"),
]