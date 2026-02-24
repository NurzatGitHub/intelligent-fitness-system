from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken


from .models import CustomUser
from .serializers import RegisterSerializer, UserSerializer


def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    """
    POST /api/users/register/
    Body: {
        "email": "...", "password": "...",
        "age": 25, "height_cm": 175, "weight_kg": 70.0,
        "fitness_level": "beginner",
        "goal": "Lose weight",
        "limitations": "No issues",
        "frequency": "3-4"
    }
    """
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.save()
    tokens = _tokens_for_user(user)

    return Response(
        {
            "user": UserSerializer(user).data,
            "access": tokens["access"],
            "refresh": tokens["refresh"],
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    """
    POST /api/users/login/
    Body: { "email": "...", "password": "..." }
    """
    email = request.data.get("email", "").strip()
    password = request.data.get("password", "")

    if not email or not password:
        return Response(
            {"error": "Email and password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        return Response(
            {"error": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.check_password(password):
        return Response(
            {"error": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_active:
        return Response(
            {"error": "Account is disabled"},
            status=status.HTTP_403_FORBIDDEN,
        )

    tokens = _tokens_for_user(user)

    return Response(
        {
            "user": UserSerializer(user).data,
            "access": tokens["access"],
            "refresh": tokens["refresh"],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """GET /api/users/me/ — возвращает профиль текущего пользователя"""
    return Response(UserSerializer(request.user).data)


from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

@api_view(["POST"])
@permission_classes([AllowAny])
def google_login(request):
    """
    POST /api/users/google/
    Body: { "id_token": "..." }
    """
    token = request.data.get("id_token")
    if not token:
        return Response({"error": "id_token is required"}, status=400)

    try:
        info = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
        email = info.get("email")
        name = info.get("name") or (email.split("@")[0] if email else "")
        if not email:
            return Response({"error": "Email not found in token"}, status=400)
    except Exception:
        return Response({"error": "Invalid Google token"}, status=401)

    user, created = CustomUser.objects.get_or_create(
        email=email,
        defaults={
            "username": email.split("@")[0],
            "first_name": name,
        }
    )

    tokens = _tokens_for_user(user)

    return Response({
        "user": UserSerializer(user).data,
        "access": tokens["access"],
        "refresh": tokens["refresh"],
        "is_new_user": created,
    })