from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)

    age = models.PositiveIntegerField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True, help_text="kg")
    height = models.FloatField(null=True, blank=True, help_text="cm")
    fitness_level = models.CharField(
        max_length=20,
        choices=[
            ("beginner", "Beginner"),
            ("intermediate", "Intermediate"),
            ("advanced", "Advanced"),
        ],
        default="beginner",
    )

    goal = models.CharField(max_length=100, blank=True, default="")
    limitations = models.CharField(max_length=200, blank=True, default="")
    frequency = models.CharField(max_length=20, blank=True, default="")

    workout_duration = models.CharField(max_length=20, blank=True, default="")
    workout_place = models.CharField(max_length=30, blank=True, default="")
    endurance_level = models.CharField(max_length=20, blank=True, default="")
    gender = models.CharField(max_length=20, blank=True, default="")

    profile_picture = models.ImageField(upload_to="profile_pics/", null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email

    class Meta:
        app_label = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"