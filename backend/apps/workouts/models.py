from django.conf import settings
from django.db import models


class WorkoutSession(models.Model):
    STATUS_CHOICES = [
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("in_progress", "In Progress"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workout_sessions",
    )

    weekly_plan_day = models.ForeignKey(
        "assistant.WeeklyPlanDay",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workout_sessions",
    )

    title = models.CharField(max_length=150, blank=True, default="")
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField()
    total_duration_sec = models.PositiveIntegerField(default=0)
    total_reps = models.PositiveIntegerField(default=0)
    avg_form_score = models.FloatField(null=True, blank=True)
    calories_burned = models.PositiveIntegerField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="completed",
    )

    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-finished_at", "-created_at"]
        indexes = [
            models.Index(fields=["user", "-finished_at"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"WorkoutSession<{self.user_id}, {self.title}, {self.finished_at}>"


class WorkoutExercise(models.Model):
    workout_session = models.ForeignKey(
        WorkoutSession,
        on_delete=models.CASCADE,
        related_name="exercises",
    )

    exercise = models.ForeignKey(
        "exercises.Exercise",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workout_exercises",
    )

    exercise_name = models.CharField(max_length=150, blank=True, default="")
    exercise_slug = models.CharField(max_length=180, blank=True, default="")

    sort_order = models.PositiveSmallIntegerField(default=0)

    completed_sets = models.PositiveIntegerField(null=True, blank=True)
    completed_reps = models.PositiveIntegerField(default=0)
    duration_sec = models.PositiveIntegerField(default=0)
    avg_form_score = models.FloatField(null=True, blank=True)

    detected_mistake = models.CharField(max_length=150, blank=True, default="")
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        name = self.exercise.name if self.exercise else self.exercise_name
        return f"{self.workout_session_id} • {name}"


class UserProgressSnapshot(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="progress_snapshot",
    )

    total_workouts = models.PositiveIntegerField(default=0)
    total_reps = models.PositiveIntegerField(default=0)
    average_form_score = models.FloatField(default=0)
    current_streak = models.PositiveIntegerField(default=0)
    best_exercise = models.CharField(max_length=150, blank=True, default="")
    last_workout_at = models.DateTimeField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Progress<{self.user_id}>"