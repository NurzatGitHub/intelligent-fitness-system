from django.contrib import admin
from .models import ExerciseCategory, ExerciseSubcategory, Exercise


@admin.register(ExerciseCategory)
class ExerciseCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("sort_order", "name")


@admin.register(ExerciseSubcategory)
class ExerciseSubcategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "slug", "is_active", "sort_order")
    list_filter = ("category", "is_active")
    search_fields = ("name", "slug", "category__name")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("category__sort_order", "sort_order", "name")


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "category",
        "subcategory",
        "difficulty",
        "equipment",
        "is_active",
        "sort_order",
    )
    list_filter = ("category", "subcategory", "difficulty", "is_active")
    search_fields = ("name", "slug", "target_muscle", "equipment")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("category__sort_order", "subcategory__sort_order", "sort_order", "name")