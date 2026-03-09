from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    def fitness_badge(self, obj):
        colors = {
            "beginner": "#22c55e",
            "intermediate": "#f59e0b",
            "advanced": "#ef4444",
        }
        label = (obj.fitness_level or "").capitalize()
        color = colors.get(obj.fitness_level, "#6b7280")
        return format_html(
            '<span style="padding:4px 8px;border-radius:12px;'
            'background:{};color:white;font-weight:600;">{}</span>',
            color,
            label or "-"
        )
    fitness_badge.short_description = "Fitness level"

    def height_display(self, obj):
        return f"{obj.height} cm" if obj.height else "-"
    height_display.short_description = "Height"

    def weight_display(self, obj):
        return f"{obj.weight} kg" if obj.weight else "-"
    weight_display.short_description = "Weight"

    def avatar_preview(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" style="height:40px;width:40px;border-radius:50%;object-fit:cover;" />',
                obj.profile_picture.url
            )
        return "-"
    avatar_preview.short_description = "Avatar"

    list_display = (
        "id",
        "avatar_preview",
        "email",
        "username",
        "height_display",
        "weight_display",
        "fitness_badge",
        "goal",
        "frequency",
        "gender",
        "workout_place",
        "endurance_level",
        "workout_duration",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "fitness_level",
        "gender",
        "workout_place",
        "endurance_level",
        "is_staff",
        "is_active",
    )

    search_fields = ("email", "username", "goal", "limitations")
    ordering = ("-id",)

    readonly_fields = ("id", "last_login", "date_joined", "avatar_preview")

    fieldsets = UserAdmin.fieldsets + (
        ("Fitness Profile", {
            "fields": (
                "age",
                "height",
                "weight",
                "fitness_level",
                "goal",
                "limitations",
                "frequency",
                "gender",
                "workout_place",
                "endurance_level",
                "workout_duration",
                "profile_picture",
                "avatar_preview",
            )
        }),
    )