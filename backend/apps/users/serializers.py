from rest_framework import serializers
from .models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = (
            "id", "email", "username",
            "age", "weight", "height", "fitness_level",
            "goal", "limitations", "frequency",
        )
        read_only_fields = ("id",)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = CustomUser
        fields = (
            "email", "password",
            "age", "height", "weight",
            "fitness_level", "goal", "limitations", "frequency",
        )

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        # username = часть email до @
        username = validated_data["email"].split("@")[0]
        # если такой username уже есть — добавляем цифру
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
        )