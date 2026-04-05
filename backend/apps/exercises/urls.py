from django.urls import path
from .views import category_list, subcategory_list, exercise_list, exercise_detail

urlpatterns = [
    path("categories/", category_list, name="exercise-category-list"),
    path("subcategories/", subcategory_list, name="exercise-subcategory-list"),
    path("", exercise_list, name="exercise-list"),
    path("<slug:slug>/", exercise_detail, name="exercise-detail"),
]