from rest_framework import serializers
from .models import ExerciseCategory, ExerciseSubcategory, Exercise


class ExerciseCategorySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    subcategories_count = serializers.IntegerField(source="subcategories.count", read_only=True)
    exercises_count = serializers.IntegerField(source="exercises.count", read_only=True)

    class Meta:
        model = ExerciseCategory
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "image_url",
            "is_active",
            "sort_order",
            "subcategories_count",
            "exercises_count",
        )

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image:
            url = obj.image.url
            return request.build_absolute_uri(url) if request else url
        return None


class ExerciseSubcategorySerializer(serializers.ModelSerializer):
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = ExerciseSubcategory
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "is_active",
            "sort_order",
            "category",
            "category_name",
            "category_slug",
        )


class ExerciseListSerializer(serializers.ModelSerializer):
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    subcategory_slug = serializers.CharField(source="subcategory.slug", read_only=True, default=None)
    subcategory_name = serializers.CharField(source="subcategory.name", read_only=True, default=None)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Exercise
        fields = (
            "id",
            "external_id",
            "name",
            "slug",
            "description",
            "target_muscle",
            "equipment",
            "difficulty",
            "default_sets",
            "default_reps",
            "default_duration_min",
            "image_url",
            "asset_image_name",
            "asset_video_name",
            "category",
            "category_name",
            "category_slug",
            "subcategory",
            "subcategory_name",
            "subcategory_slug",
        )

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image:
            url = obj.image.url
            return request.build_absolute_uri(url) if request else url
        return None


class ExerciseDetailSerializer(serializers.ModelSerializer):
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    subcategory_slug = serializers.CharField(source="subcategory.slug", read_only=True, default=None)
    subcategory_name = serializers.CharField(source="subcategory.name", read_only=True, default=None)
    image_url = serializers.SerializerMethodField()
    steps = serializers.SerializerMethodField()
    tips_list = serializers.SerializerMethodField()

    class Meta:
        model = Exercise
        fields = (
            "id",
            "external_id",
            "name",
            "slug",
            "description",
            "target_muscle",
            "equipment",
            "difficulty",
            "instructions",
            "tips",
            "steps",
            "tips_list",
            "video_url",
            "image_url",
            "asset_image_name",
            "asset_video_name",
            "default_sets",
            "default_reps",
            "default_duration_min",
            "category",
            "category_name",
            "category_slug",
            "subcategory",
            "subcategory_name",
            "subcategory_slug",
            "is_active",
            "sort_order",
        )

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image:
            url = obj.image.url
            return request.build_absolute_uri(url) if request else url
        return None

    def get_steps(self, obj):
        return [line.strip() for line in obj.instructions.splitlines() if line.strip()]

    def get_tips_list(self, obj):
        return [line.strip() for line in obj.tips.splitlines() if line.strip()]