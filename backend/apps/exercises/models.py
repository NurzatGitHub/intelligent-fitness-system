from django.db import models


class ExerciseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True, default="")
    image = models.ImageField(upload_to="exercise_categories/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Exercise Category"
        verbose_name_plural = "Exercise Categories"

    def __str__(self):
        return self.name


class ExerciseSubcategory(models.Model):
    category = models.ForeignKey(
        ExerciseCategory,
        on_delete=models.CASCADE,
        related_name="subcategories"
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["category__sort_order", "sort_order", "name"]
        unique_together = ("category", "slug")
        verbose_name = "Exercise Subcategory"
        verbose_name_plural = "Exercise Subcategories"

    def __str__(self):
        return f"{self.category.name} • {self.name}"


class Exercise(models.Model):
    DIFFICULTY_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]

    category = models.ForeignKey(
        ExerciseCategory,
        on_delete=models.CASCADE,
        related_name="exercises"
    )
    subcategory = models.ForeignKey(
        ExerciseSubcategory,
        on_delete=models.SET_NULL,
        related_name="exercises",
        null=True,
        blank=True
    )

    external_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(blank=True, default="")

    target_muscle = models.CharField(max_length=120, blank=True, default="")
    equipment = models.CharField(max_length=120, blank=True, default="")
    difficulty = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        default="beginner"
    )

    instructions = models.TextField(blank=True, default="")
    tips = models.TextField(blank=True, default="")

    image = models.ImageField(upload_to="exercises/", null=True, blank=True)
    video_url = models.URLField(blank=True, default="")

    asset_image_name = models.CharField(max_length=150, blank=True, default="")
    asset_video_name = models.CharField(max_length=150, blank=True, default="")

    default_sets = models.PositiveIntegerField(null=True, blank=True)
    default_reps = models.PositiveIntegerField(null=True, blank=True)
    default_duration_min = models.PositiveIntegerField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category__sort_order", "subcategory__sort_order", "sort_order", "name"]
        verbose_name = "Exercise"
        verbose_name_plural = "Exercises"

    def __str__(self):
        return f"{self.name} ({self.external_id})"