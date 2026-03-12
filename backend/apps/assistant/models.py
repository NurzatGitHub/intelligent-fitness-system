from django.conf import settings
from django.db import models


class WeeklyPlan(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weekly_plan"
    )
    plan_json = models.JSONField(default=dict)
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"WeeklyPlan<{self.user.email}>"