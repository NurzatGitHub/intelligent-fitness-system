from django.contrib import admin
from .models import WeeklyPlan, WeeklyPlanDay, WeeklyPlanExercise


class WeeklyPlanExerciseInline(admin.TabularInline):
    model = WeeklyPlanExercise
    extra = 0
    autocomplete_fields = ("exercise",)
    fields = ("sort_order", "exercise", "sets", "reps", "duration_min", "notes")


class WeeklyPlanDayInline(admin.StackedInline):
    model = WeeklyPlanDay
    extra = 0
    fields = ("day_of_week", "label", "day_type", "title", "description", "duration_min", "note", "sort_order")
    show_change_link = True


@admin.register(WeeklyPlan)
class WeeklyPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "week_start_date", "title", "is_active", "created_at", "updated_at")
    list_filter = ("is_active", "week_start_date", "created_at")
    search_fields = ("user__username", "user__email", "title", "summary")
    ordering = ("-week_start_date", "-created_at")
    inlines = (WeeklyPlanDayInline,)
    readonly_fields = ("created_at", "updated_at")


@admin.register(WeeklyPlanDay)
class WeeklyPlanDayAdmin(admin.ModelAdmin):
    list_display = ("id", "weekly_plan", "day_of_week", "label", "day_type", "title", "duration_min", "sort_order")
    list_filter = ("day_type", "day_of_week")
    search_fields = ("title", "note", "weekly_plan__user__email", "weekly_plan__user__username")
    ordering = ("weekly_plan", "sort_order", "day_of_week")
    inlines = (WeeklyPlanExerciseInline,)


@admin.register(WeeklyPlanExercise)
class WeeklyPlanExerciseAdmin(admin.ModelAdmin):
    list_display = ("id", "weekly_plan_day", "exercise", "sort_order", "sets", "reps", "duration_min")
    list_filter = ("exercise__category", "exercise__difficulty")
    search_fields = (
        "exercise__name",
        "exercise__slug",
        "weekly_plan_day__title",
        "weekly_plan_day__weekly_plan__user__email",
    )
    ordering = ("weekly_plan_day", "sort_order")
    autocomplete_fields = ("exercise",)