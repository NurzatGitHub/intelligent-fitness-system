from rest_framework import serializers
from .models import WorkoutSession, WorkoutExercise, UserProgressSnapshot


class WorkoutExerciseWriteSerializer(serializers.Serializer):
    exercise_slug = serializers.CharField(required=False, allow_blank=True, default="")
    exercise_name = serializers.CharField(required=False, allow_blank=True, default="")
    completed_sets = serializers.IntegerField(required=False, allow_null=True)
    completed_reps = serializers.IntegerField(required=False, default=0)
    duration_sec = serializers.IntegerField(required=False, default=0)
    avg_form_score = serializers.FloatField(required=False, allow_null=True)
    detected_mistake = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class WorkoutSessionCreateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, default="")
    weekly_plan_day_id = serializers.IntegerField(required=False, allow_null=True)
    started_at = serializers.DateTimeField(required=False, allow_null=True)
    finished_at = serializers.DateTimeField(required=False, allow_null=True)
    total_duration_sec = serializers.IntegerField(required=False, default=0)
    total_reps = serializers.IntegerField(required=False, default=0)
    avg_form_score = serializers.FloatField(required=False, allow_null=True)
    calories_burned = serializers.IntegerField(required=False, allow_null=True)
    status = serializers.CharField(required=False, allow_blank=True, default="completed")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    exercises = WorkoutExerciseWriteSerializer(many=True, required=False)


class WorkoutExerciseReadSerializer(serializers.ModelSerializer):
    exercise_id = serializers.IntegerField(source="exercise.id", read_only=True)
    exercise_display_name = serializers.SerializerMethodField()

    class Meta:
        model = WorkoutExercise
        fields = (
            "id",
            "exercise_id",
            "exercise_name",
            "exercise_slug",
            "exercise_display_name",
            "sort_order",
            "completed_sets",
            "completed_reps",
            "duration_sec",
            "avg_form_score",
            "detected_mistake",
            "notes",
        )

    def get_exercise_display_name(self, obj):
        if obj.exercise and obj.exercise.name:
            return obj.exercise.name
        return obj.exercise_name


class WorkoutSessionReadSerializer(serializers.ModelSerializer):
    exercises = WorkoutExerciseReadSerializer(many=True, read_only=True)

    class Meta:
        model = WorkoutSession
        fields = (
            "id",
            "title",
            "started_at",
            "finished_at",
            "total_duration_sec",
            "total_reps",
            "avg_form_score",
            "calories_burned",
            "status",
            "notes",
            "created_at",
            "exercises",
        )


class UserProgressSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProgressSnapshot
        fields = (
            "total_workouts",
            "total_reps",
            "average_form_score",
            "current_streak",
            "best_exercise",
            "last_workout_at",
            "updated_at",
        )