from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    # ======= КРАСИВЫЕ КОЛОНКИ =======

    def fitness_badge(self, obj):
        colors = {
            "Beginner": "#22c55e",
            "Intermediate": "#f59e0b",
            "Advanced": "#ef4444",
        }
        color = colors.get(obj.fitness_level, "#6b7280")
        return format_html(
            '<span style="padding:4px 8px;border-radius:12px;'
            'background:{};color:white;font-weight:600;">{}</span>',
            color,
            obj.fitness_level
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

    # ======= СПИСОК =======

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
        "is_staff",
        "is_active",
    )

    list_filter = ("fitness_level", "is_staff", "is_active")
    search_fields = ("email", "username")
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
                "profile_picture",
                "avatar_preview",
            )
        }),
    )