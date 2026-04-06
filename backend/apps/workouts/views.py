from collections import Counter
from datetime import timedelta

from django.db import transaction
from django.db.models import Sum, Avg
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from assistant.models import WeeklyPlanDay
from exercises.models import Exercise
from .models import WorkoutSession, WorkoutExercise, UserProgressSnapshot
from .serializers import (
    WorkoutSessionCreateSerializer,
    WorkoutSessionReadSerializer,
    UserProgressSnapshotSerializer,
)


def _calculate_streak(sessions):
    if not sessions:
        return 0

    workout_days = sorted(
        {
            timezone.localtime(session.finished_at).date()
            for session in sessions
            if session.finished_at
        },
        reverse=True,
    )

    if not workout_days:
        return 0

    today = timezone.localdate()
    yesterday = today - timedelta(days=1)

    first_day = workout_days[0]
    if first_day not in (today, yesterday):
        return 0

    streak = 1
    current_day = first_day

    for next_day in workout_days[1:]:
        if next_day == current_day - timedelta(days=1):
            streak += 1
            current_day = next_day
        elif next_day == current_day:
            continue
        else:
            break

    return streak


def _refresh_user_progress(user):
    sessions = list(
        WorkoutSession.objects.filter(user=user, status="completed")
        .prefetch_related("exercises")
        .order_by("-finished_at", "-created_at")
    )

    total_workouts = len(sessions)
    total_reps = sum(session.total_reps or 0 for session in sessions)

    scores = [session.avg_form_score for session in sessions if session.avg_form_score is not None]
    average_form_score = round(sum(scores) / len(scores), 2) if scores else 0

    exercise_counter = Counter()
    for session in sessions:
        for exercise_item in session.exercises.all():
            name = (
                exercise_item.exercise.name
                if exercise_item.exercise and exercise_item.exercise.name
                else exercise_item.exercise_name
            )
            if name:
                exercise_counter[name] += 1

    best_exercise = exercise_counter.most_common(1)[0][0] if exercise_counter else ""
    current_streak = _calculate_streak(sessions)
    last_workout_at = sessions[0].finished_at if sessions else None

    snapshot, _ = UserProgressSnapshot.objects.update_or_create(
        user=user,
        defaults={
            "total_workouts": total_workouts,
            "total_reps": total_reps,
            "average_form_score": average_form_score,
            "current_streak": current_streak,
            "best_exercise": best_exercise,
            "last_workout_at": last_workout_at,
        },
    )
    return snapshot


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def create_workout_session(request):
    serializer = WorkoutSessionCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    started_at = data.get("started_at") or timezone.now()
    finished_at = data.get("finished_at") or timezone.now()

    weekly_plan_day = None
    weekly_plan_day_id = data.get("weekly_plan_day_id")
    if weekly_plan_day_id:
        weekly_plan_day = WeeklyPlanDay.objects.filter(
            id=weekly_plan_day_id,
            weekly_plan__user=request.user,
        ).first()

    session = WorkoutSession.objects.create(
        user=request.user,
        weekly_plan_day=weekly_plan_day,
        title=data.get("title", ""),
        started_at=started_at,
        finished_at=finished_at,
        total_duration_sec=max(0, data.get("total_duration_sec", 0)),
        total_reps=max(0, data.get("total_reps", 0)),
        avg_form_score=data.get("avg_form_score"),
        calories_burned=data.get("calories_burned"),
        status=data.get("status") or "completed",
        notes=data.get("notes", ""),
    )

    exercises_data = data.get("exercises", [])
    for index, item in enumerate(exercises_data):
        exercise = None
        exercise_slug = item.get("exercise_slug", "").strip()
        if exercise_slug:
            exercise = Exercise.objects.filter(slug=exercise_slug).first()

        exercise_name = item.get("exercise_name", "").strip()
        if not exercise_name and exercise:
            exercise_name = exercise.name

        WorkoutExercise.objects.create(
            workout_session=session,
            exercise=exercise,
            exercise_name=exercise_name,
            exercise_slug=exercise_slug or (exercise.slug if exercise else ""),
            sort_order=index,
            completed_sets=item.get("completed_sets"),
            completed_reps=max(0, item.get("completed_reps", 0)),
            duration_sec=max(0, item.get("duration_sec", 0)),
            avg_form_score=item.get("avg_form_score"),
            detected_mistake=item.get("detected_mistake", ""),
            notes=item.get("notes", ""),
        )

    snapshot = _refresh_user_progress(request.user)

    return Response(
        {
            "session": WorkoutSessionReadSerializer(session).data,
            "stats": UserProgressSnapshotSerializer(snapshot).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def workout_history(request):
    sessions = (
        WorkoutSession.objects.filter(user=request.user, status="completed")
        .prefetch_related("exercises")
        .order_by("-finished_at", "-created_at")
    )
    return Response(WorkoutSessionReadSerializer(sessions, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def workout_stats(request):
    snapshot = _refresh_user_progress(request.user)
    return Response(UserProgressSnapshotSerializer(snapshot).data)