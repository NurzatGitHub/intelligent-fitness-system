from django.conf import settings
from django.db import models


class WeeklyPlan(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weekly_plans",
    )
    title = models.CharField(max_length=120, default="AI Weekly Plan")
    summary = models.CharField(max_length=255, blank=True, default="")
    today_tip = models.CharField(max_length=255, blank=True, default="")

    week_start_date = models.DateField()
    is_active = models.BooleanField(default=True)

    # Чтобы потом можно было понимать, нужно ли регенерировать план
    profile_snapshot = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-week_start_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "week_start_date", "is_active"],
                name="unique_active_weekly_plan_per_user_week",
            )
        ]
        indexes = [
            models.Index(fields=["user", "week_start_date"]),
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self):
        return f"WeeklyPlan<{self.user_id}, {self.week_start_date}, active={self.is_active}>"


class WeeklyPlanDay(models.Model):
    DAY_CHOICES = [
        (0, "Mon"),
        (1, "Tue"),
        (2, "Wed"),
        (3, "Thu"),
        (4, "Fri"),
        (5, "Sat"),
        (6, "Sun"),
    ]

    DAY_TYPE_CHOICES = [
        ("workout", "Workout"),
        ("rest", "Rest"),
        ("recovery", "Recovery"),
    ]

    weekly_plan = models.ForeignKey(
        WeeklyPlan,
        on_delete=models.CASCADE,
        related_name="days",
    )
    day_of_week = models.PositiveSmallIntegerField(choices=DAY_CHOICES)
    label = models.CharField(max_length=12, blank=True, default="")
    day_type = models.CharField(
        max_length=20,
        choices=DAY_TYPE_CHOICES,
        default="rest",
    )
    title = models.CharField(max_length=120, blank=True, default="")
    description = models.TextField(blank=True, default="")
    duration_min = models.PositiveIntegerField(default=20)
    note = models.CharField(max_length=255, blank=True, default="")
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "day_of_week", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["weekly_plan", "day_of_week"],
                name="unique_day_per_weekly_plan",
            )
        ]

    def __str__(self):
        return f"{self.weekly_plan_id} • day={self.day_of_week} • {self.title}"


class WeeklyPlanExercise(models.Model):
    weekly_plan_day = models.ForeignKey(
        WeeklyPlanDay,
        on_delete=models.CASCADE,
        related_name="plan_exercises",
    )
    exercise = models.ForeignKey(
        "exercises.Exercise",
        on_delete=models.PROTECT,
        related_name="weekly_plan_links",
    )

    sort_order = models.PositiveSmallIntegerField(default=0)

    sets = models.PositiveIntegerField(null=True, blank=True)
    reps = models.PositiveIntegerField(null=True, blank=True)
    duration_min = models.PositiveIntegerField(null=True, blank=True)

    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.weekly_plan_day_id} • {self.exercise.name}"