from django.contrib import admin
from .models import WorkoutSession, WorkoutExercise, UserProgressSnapshot


class WorkoutExerciseInline(admin.TabularInline):
    model = WorkoutExercise
    extra = 0
    fields = (
        "sort_order",
        "exercise",
        "exercise_name",
        "exercise_slug",
        "completed_sets",
        "completed_reps",
        "duration_sec",
        "avg_form_score",
        "detected_mistake",
        "notes",
    )
    autocomplete_fields = ("exercise",)


@admin.register(WorkoutSession)
class WorkoutSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "title",
        "status",
        "total_duration_sec",
        "total_reps",
        "avg_form_score",
        "finished_at",
    )
    list_filter = ("status", "finished_at", "created_at")
    search_fields = ("user__email", "user__username", "title", "notes")
    ordering = ("-finished_at", "-created_at")
    inlines = (WorkoutExerciseInline,)


@admin.register(WorkoutExercise)
class WorkoutExerciseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "workout_session",
        "exercise",
        "exercise_name",
        "completed_reps",
        "duration_sec",
        "avg_form_score",
    )
    search_fields = (
        "exercise__name",
        "exercise_name",
        "exercise_slug",
        "workout_session__user__email",
    )
    autocomplete_fields = ("exercise",)


@admin.register(UserProgressSnapshot)
class UserProgressSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "total_workouts",
        "total_reps",
        "average_form_score",
        "current_streak",
        "best_exercise",
        "updated_at",
    )
    search_fields = ("user__email", "user__username", "best_exercise")