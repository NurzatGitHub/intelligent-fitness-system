from rest_framework import serializers
from .models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            "id", "email", "username",
            "age", "weight", "height", "fitness_level",
            "goal", "limitations", "frequency",
            "workout_duration", "workout_place", "endurance_level", "gender",
            "profile_picture_url",
        )
        read_only_fields = ("id", "profile_picture_url")

    def get_profile_picture_url(self, obj):
        request = self.context.get("request")
        if obj.profile_picture:
            url = obj.profile_picture.url
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        return None


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = CustomUser
        fields = (
            "email", "password",
            "age", "height", "weight",
            "fitness_level", "goal", "limitations", "frequency",
            "workout_duration", "workout_place", "endurance_level", "gender",
        )

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        username = validated_data["email"].split("@")[0]
        base = username
        counter = 1
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1

        return CustomUser.objects.create_user(
            email=validated_data["email"],
            username=username,
            password=validated_data["password"],
            age=validated_data.get("age"),
            weight=validated_data.get("weight"),
            height=validated_data.get("height"),
            fitness_level=validated_data.get("fitness_level", "beginner"),
            goal=validated_data.get("goal", ""),
            limitations=validated_data.get("limitations", ""),
            frequency=validated_data.get("frequency", ""),
            workout_duration=validated_data.get("workout_duration", ""),
            workout_place=validated_data.get("workout_place", ""),
            endurance_level=validated_data.get("endurance_level", ""),
            gender=validated_data.get("gender", ""),
        )


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = (
            "username",
            "age", "height", "weight",
            "fitness_level", "goal", "limitations", "frequency",
            "workout_duration", "workout_place", "endurance_level", "gender",
        )


class AvatarUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ("profile_picture",)

    def validate_profile_picture(self, value):
        max_size = 5 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("Image is too large. Max size is 5MB.")
        return value