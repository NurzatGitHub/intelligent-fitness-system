from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import ExerciseCategory, ExerciseSubcategory, Exercise
from .serializers import (
    ExerciseCategorySerializer,
    ExerciseSubcategorySerializer,
    ExerciseListSerializer,
    ExerciseDetailSerializer,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def category_list(request):
    queryset = ExerciseCategory.objects.filter(is_active=True).order_by("sort_order", "name")
    serializer = ExerciseCategorySerializer(queryset, many=True, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subcategory_list(request):
    category_slug = request.query_params.get("category")

    queryset = ExerciseSubcategory.objects.filter(is_active=True)

    if category_slug:
        queryset = queryset.filter(category__slug=category_slug, category__is_active=True)

    queryset = queryset.order_by("category__sort_order", "sort_order", "name")

    serializer = ExerciseSubcategorySerializer(queryset, many=True, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def exercise_list(request):
    category_slug = request.query_params.get("category")
    subcategory_slug = request.query_params.get("subcategory")
    search = request.query_params.get("search")

    queryset = Exercise.objects.filter(
        is_active=True,
        category__is_active=True,
    ).select_related("category", "subcategory")

    if category_slug:
        queryset = queryset.filter(category__slug=category_slug)

    if subcategory_slug:
        queryset = queryset.filter(subcategory__slug=subcategory_slug)

    if search:
        queryset = queryset.filter(name__icontains=search.strip())

    queryset = queryset.order_by("category__sort_order", "subcategory__sort_order", "sort_order", "name")

    serializer = ExerciseListSerializer(queryset, many=True, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def exercise_detail(request, slug):
    try:
        exercise = Exercise.objects.select_related("category", "subcategory").get(
            slug=slug,
            is_active=True,
            category__is_active=True,
        )
    except Exercise.DoesNotExist:
        return Response({"detail": "Exercise not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = ExerciseDetailSerializer(exercise, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)