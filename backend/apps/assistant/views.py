import os
import json
from collections import defaultdict
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import UserRateThrottle

from google import genai

from .models import WeeklyPlan, WeeklyPlanDay, WeeklyPlanExercise
from exercises.models import Exercise
from workouts.models import WorkoutSession


class AssistantChatThrottle(UserRateThrottle):
    scope = "assistant_chat"


DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _safe(value, default="not specified"):
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _get_current_week_start():
    today = timezone.localdate()
    return today - timedelta(days=today.weekday())


def _day_key_from_index(index: int) -> str:
    return DAY_KEYS[index]


def _day_label_from_index(index: int) -> str:
    return DAY_LABELS[index]


def _serialize_plan(plan: WeeklyPlan, user) -> dict:
    sessions = (
        WorkoutSession.objects.filter(
            user=user,
            status="completed",
            weekly_plan_day__weekly_plan=plan,
        )
        .prefetch_related("exercises__exercise")
        .order_by("-finished_at", "-created_at")
    )

    completed_day_sessions = set()
    completed_slugs_by_day = defaultdict(set)

    for session in sessions:
        day_id = session.weekly_plan_day_id
        if not day_id:
            continue

        completed_day_sessions.add(day_id)

        for ex_item in session.exercises.all():
            slug = (ex_item.exercise_slug or "").strip()
            if not slug and ex_item.exercise:
                slug = ex_item.exercise.slug
            if slug:
                completed_slugs_by_day[day_id].add(slug)

    days_qs = (
        plan.days.all()
        .prefetch_related("plan_exercises__exercise")
        .order_by("sort_order", "day_of_week", "id")
    )

    days = []
    for day in days_qs:
        exercises = []
        total_exercise_count = 0
        completed_exercise_count = 0

        for item in day.plan_exercises.all().order_by("sort_order", "id"):
            ex = item.exercise
            is_completed = ex.slug in completed_slugs_by_day[day.id]

            total_exercise_count += 1
            if is_completed:
                completed_exercise_count += 1

            exercises.append(
                {
                    "id": ex.id,
                    "external_id": ex.external_id,
                    "name": ex.name,
                    "slug": ex.slug,
                    "description": ex.description,
                    "target_muscle": ex.target_muscle,
                    "equipment": ex.equipment,
                    "difficulty": ex.difficulty,
                    "asset_image_name": ex.asset_image_name,
                    "asset_video_name": ex.asset_video_name,
                    "default_sets": ex.default_sets,
                    "default_reps": ex.default_reps,
                    "default_duration_min": ex.default_duration_min,
                    "plan_sets": item.sets,
                    "plan_reps": item.reps,
                    "plan_duration_min": item.duration_min,
                    "plan_notes": item.notes,
                    "sort_order": item.sort_order,
                    "is_completed": is_completed,
                }
            )

        if total_exercise_count > 0:
            day_is_completed = completed_exercise_count == total_exercise_count
        else:
            day_is_completed = day.id in completed_day_sessions

        days.append(
            {
                "id": day.id,
                "day_key": _day_key_from_index(day.day_of_week),
                "label": day.label or _day_label_from_index(day.day_of_week),
                "type": day.day_type,
                "title": day.title,
                "description": day.description,
                "duration_min": day.duration_min,
                "note": day.note,
                "sort_order": day.sort_order,
                "is_completed": day_is_completed,
                "completed_exercise_count": completed_exercise_count,
                "total_exercise_count": total_exercise_count,
                "exercises": exercises,
            }
        )

    return {
        "id": plan.id,
        "title": plan.title or "AI Weekly Plan",
        "goal_summary": plan.summary or "Personalized weekly training plan",
        "today_tip": plan.today_tip or "Focus on form and consistency",
        "week_start_date": str(plan.week_start_date),
        "is_active": plan.is_active,
        "generated_at": plan.created_at.isoformat() if plan.created_at else None,
        "days": days,
    }


def build_user_profile_block(user) -> str:
    return (
        f"- age: {_safe(getattr(user, 'age', None))}\n"
        f"- height cm: {_safe(getattr(user, 'height', None))}\n"
        f"- weight kg: {_safe(getattr(user, 'weight', None))}\n"
        f"- gender: {_safe(getattr(user, 'gender', ''))}\n"
        f"- fitness level: {_safe(getattr(user, 'fitness_level', ''))}\n"
        f"- goal: {_safe(getattr(user, 'goal', ''))}\n"
        f"- limitations: {_safe(getattr(user, 'limitations', ''))}\n"
        f"- training frequency per week: {_safe(getattr(user, 'frequency', ''))}\n"
        f"- workout duration preference: {_safe(getattr(user, 'workout_duration', ''))}\n"
        f"- workout place: {_safe(getattr(user, 'workout_place', ''))}\n"
        f"- endurance level: {_safe(getattr(user, 'endurance_level', ''))}\n"
    )


def _build_profile_snapshot(user) -> dict:
    return {
        "age": getattr(user, "age", None),
        "height": getattr(user, "height", None),
        "weight": getattr(user, "weight", None),
        "gender": getattr(user, "gender", ""),
        "fitness_level": getattr(user, "fitness_level", ""),
        "goal": getattr(user, "goal", ""),
        "limitations": getattr(user, "limitations", ""),
        "frequency": getattr(user, "frequency", ""),
        "workout_duration": getattr(user, "workout_duration", ""),
        "workout_place": getattr(user, "workout_place", ""),
        "endurance_level": getattr(user, "endurance_level", ""),
    }


def build_system_prompt(user) -> str:
    return (
        "You are a fitness coach inside a mobile app. "
        "Answer briefly, clearly, and practically. "
        "Use the user's fitness profile to personalize the answer. "
        "If the user mentions pain or injury, advise them to stop and consult a professional. "
        "Do not give medical diagnosis.\n\n"
        "User profile:\n"
        f"{build_user_profile_block(user)}"
    )


def _pick_exercises_for_day(day_type: str, title: str, user):
    if day_type != "workout":
        return []

    qs = Exercise.objects.filter(is_active=True).select_related("category", "subcategory")

    fitness_level = str(getattr(user, "fitness_level", "") or "").strip().lower()
    workout_place = str(getattr(user, "workout_place", "") or "").strip().lower()
    title_lower = (title or "").lower()

    if fitness_level in ("beginner", "intermediate", "advanced"):
        allowed_difficulties = ["beginner"]
        if fitness_level == "intermediate":
            allowed_difficulties = ["beginner", "intermediate"]
        elif fitness_level == "advanced":
            allowed_difficulties = ["beginner", "intermediate", "advanced"]
        qs = qs.filter(difficulty__in=allowed_difficulties)

    if any(x in workout_place for x in ["home", "house", "apartment"]):
        qs = qs.exclude(equipment__iregex=r"(machine|barbell|smith|cable)")

    keyword_to_category = [
        (["chest"], "chest"),
        (["back", "lats"], "back"),
        (["legs", "glutes", "quads", "hamstrings", "calves"], "legs"),
        (["abs", "core"], "abs"),
        (["cardio", "hiit"], "cardio"),
        (["arms", "biceps", "triceps"], "arms"),
    ]

    matched_category_slug = None
    for keywords, category_slug in keyword_to_category:
        if any(word in title_lower for word in keywords):
            matched_category_slug = category_slug
            break

    if matched_category_slug:
        filtered = list(qs.filter(category__slug=matched_category_slug).order_by("sort_order", "name")[:6])
        if filtered:
            return filtered[:4]

    return list(qs.order_by("category__sort_order", "subcategory__sort_order", "sort_order", "name")[:4])


def build_weekly_plan_prompt(user) -> str:
    return (
        "You are a fitness coach inside a mobile app.\n"
        "Generate a practical weekly training plan personalized to the user's profile.\n"
        "Respect injuries, limitations, fitness level, training frequency, workout duration, workout place, and endurance level.\n"
        "Do not give medical diagnosis.\n"
        "If limitations suggest caution, make the plan safer and lighter.\n\n"
        "Return ONLY valid JSON. No markdown. No explanation. No code fences.\n\n"
        "Required JSON format:\n"
        "{\n"
        '  "title": "AI Weekly Plan",\n'
        '  "goal_summary": "short 1-sentence summary",\n'
        '  "days": [\n'
        '    {"day_key":"mon","label":"Mon","type":"workout","title":"Chest + Triceps","duration_min":45,"note":"short tip"},\n'
        '    {"day_key":"tue","label":"Tue","type":"rest","title":"Recovery","duration_min":20,"note":"short tip"},\n'
        '    {"day_key":"wed","label":"Wed","type":"workout","title":"Back + Biceps","duration_min":45,"note":"short tip"},\n'
        '    {"day_key":"thu","label":"Thu","type":"rest","title":"Mobility","duration_min":15,"note":"short tip"},\n'
        '    {"day_key":"fri","label":"Fri","type":"workout","title":"Legs + Core","duration_min":50,"note":"short tip"},\n'
        '    {"day_key":"sat","label":"Sat","type":"workout","title":"Full Body","duration_min":40,"note":"short tip"},\n'
        '    {"day_key":"sun","label":"Sun","type":"rest","title":"Recovery","duration_min":20,"note":"short tip"}\n'
        "  ],\n"
        '  "today_tip": "short helpful tip"\n'
        "}\n\n"
        "Rules:\n"
        "- exactly 7 days in this order: Mon, Tue, Wed, Thu, Fri, Sat, Sun\n"
        "- type must be either workout, rest, or recovery\n"
        "- duration_min must be an integer\n"
        "- title must be very short\n"
        "- note must be very short\n"
        "- goal_summary must be very short\n"
        "- keep the plan realistic for a mobile fitness app\n\n"
        "User profile:\n"
        f"{build_user_profile_block(user)}"
    )


def _extract_json_object(text: str) -> dict:
    raw = (text or "").strip()

    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()

    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("JSON object not found in Gemini response")

    raw = raw[start:end + 1]
    return json.loads(raw)


def _normalize_day(day: dict, index: int) -> dict:
    day_key = DAY_KEYS[index]
    label = DAY_LABELS[index]

    day_type = str(day.get("type", "rest")).strip().lower()
    if day_type not in ("workout", "rest", "recovery"):
        day_type = "rest"

    title = str(day.get("title", "")).strip() or ("Workout" if day_type == "workout" else "Recovery")
    note = str(day.get("note", "")).strip() or "Stay consistent"

    try:
        duration_min = int(day.get("duration_min", 20))
    except Exception:
        duration_min = 20

    duration_min = max(5, min(duration_min, 180))

    return {
        "day_key": day_key,
        "label": label,
        "type": day_type,
        "title": title[:60],
        "duration_min": duration_min,
        "note": note[:120],
    }


def _normalize_plan(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Weekly plan response is not a JSON object")

    raw_days = data.get("days")
    if not isinstance(raw_days, list) or len(raw_days) != 7:
        raise ValueError("Weekly plan must contain exactly 7 days")

    normalized_days = [_normalize_day(raw_days[i], i) for i in range(7)]

    title = str(data.get("title", "AI Weekly Plan")).strip() or "AI Weekly Plan"
    goal_summary = str(data.get("goal_summary", "")).strip() or "Personalized weekly training plan"
    today_tip = str(data.get("today_tip", "")).strip() or "Focus on form and consistency"

    return {
        "title": title[:80],
        "goal_summary": goal_summary[:180],
        "days": normalized_days,
        "today_tip": today_tip[:180],
        "generated_at": datetime.now().isoformat(),
    }


def _generate_weekly_plan_data(user) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    client = genai.Client(api_key=api_key)
    prompt = build_weekly_plan_prompt(user)

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
    )

    data = _extract_json_object(response.text or "")
    return _normalize_plan(data)


@transaction.atomic
def _create_and_save_weekly_plan(user, plan_data: dict) -> WeeklyPlan:
    week_start = _get_current_week_start()

    WeeklyPlan.objects.filter(
        user=user,
        is_active=True,
    ).exclude(week_start_date=week_start).update(is_active=False)

    WeeklyPlan.objects.filter(
        user=user,
        week_start_date=week_start,
        is_active=True,
    ).update(is_active=False)

    plan = WeeklyPlan.objects.create(
        user=user,
        title=plan_data.get("title") or "AI Weekly Plan",
        summary=plan_data.get("goal_summary") or "Personalized weekly training plan",
        today_tip=plan_data.get("today_tip") or "Focus on form and consistency",
        week_start_date=week_start,
        is_active=True,
        profile_snapshot=_build_profile_snapshot(user),
    )

    for index, day_data in enumerate(plan_data.get("days", [])):
        day = WeeklyPlanDay.objects.create(
            weekly_plan=plan,
            day_of_week=index,
            label=day_data.get("label") or _day_label_from_index(index),
            day_type=day_data.get("type") or "rest",
            title=day_data.get("title") or "",
            description="",
            duration_min=day_data.get("duration_min") or 20,
            note=day_data.get("note") or "",
            sort_order=index,
        )

        selected_exercises = _pick_exercises_for_day(
            day_type=day.day_type,
            title=day.title,
            user=user,
        )

        for exercise_index, exercise in enumerate(selected_exercises):
            WeeklyPlanExercise.objects.create(
                weekly_plan_day=day,
                exercise=exercise,
                sort_order=exercise_index,
                sets=exercise.default_sets,
                reps=exercise.default_reps,
                duration_min=exercise.default_duration_min,
                notes="",
            )

    return plan


def _get_or_create_current_week_plan(user) -> WeeklyPlan:
    week_start = _get_current_week_start()

    existing = (
        WeeklyPlan.objects.filter(
            user=user,
            week_start_date=week_start,
            is_active=True,
        )
        .prefetch_related("days__plan_exercises__exercise")
        .order_by("-created_at")
        .first()
    )
    if existing:
        return existing

    plan_data = _generate_weekly_plan_data(user)
    return _create_and_save_weekly_plan(user, plan_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([AssistantChatThrottle])
def assistant_chat(request):
    message = (request.data.get("message") or "").strip()

    if not message:
        return Response({"detail": "message is required"}, status=status.HTTP_400_BAD_REQUEST)

    if len(message) > 4000:
        return Response({"detail": "message too long"}, status=status.HTTP_400_BAD_REQUEST)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return Response({"detail": "GEMINI_API_KEY is not set"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    system_prompt = build_system_prompt(request.user)

    try:
        client = genai.Client(api_key=api_key)
        full_prompt = f"{system_prompt}\n\nUser message:\n{message}"

        response = client.models.generate_content(
            model=model_name,
            contents=full_prompt,
        )

        reply = (response.text or "").strip()
        if not reply:
            reply = "I couldn't generate a response. Please try again."

        if len(reply) > 3000:
            reply = reply[:3000]

        return Response({"reply": reply}, status=status.HTTP_200_OK)

    except Exception as e:
        error_text = str(e)

        if "RESOURCE_EXHAUSTED" in error_text or "429" in error_text:
            return Response(
                {"detail": "Gemini quota/rate limit exceeded", "error": error_text},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if "PERMISSION_DENIED" in error_text or "API key" in error_text:
            return Response(
                {"detail": "Gemini permission/key error", "error": error_text},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if "INVALID_ARGUMENT" in error_text or "404" in error_text:
            return Response(
                {"detail": "Gemini invalid model/request", "error": error_text},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": "Assistant internal error", "error": error_text},
            status=status.HTTP_502_BAD_GATEWAY,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def weekly_plan(request):
    try:
        plan = _get_or_create_current_week_plan(request.user)
        return Response(_serialize_plan(plan, request.user), status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"detail": "Failed to get weekly plan", "error": str(e)},
            status=status.HTTP_502_BAD_GATEWAY,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def regenerate_weekly_plan(request):
    try:
        WeeklyPlan.objects.filter(user=request.user, is_active=True).update(is_active=False)
        plan_data = _generate_weekly_plan_data(request.user)
        plan = _create_and_save_weekly_plan(request.user, plan_data)
        return Response(_serialize_plan(plan, request.user), status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"detail": "Failed to regenerate weekly plan", "error": str(e)},
            status=status.HTTP_502_BAD_GATEWAY,
        )