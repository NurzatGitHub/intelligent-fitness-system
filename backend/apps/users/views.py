from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    UserUpdateSerializer,
    AvatarUploadSerializer,
)

from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from assistant.models import WeeklyPlan


def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def _user_response(user, request):
    return UserSerializer(user, context={"request": request}).data


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.save()
    tokens = _tokens_for_user(user)

    return Response(
        {
            "user": _user_response(user, request),
            "access": tokens["access"],
            "refresh": tokens["refresh"],
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
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
            "user": _user_response(user, request),
            "access": tokens["access"],
            "refresh": tokens["refresh"],
        }
    )


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me(request):
    if request.method == "GET":
        return Response(_user_response(request.user, request))

    serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.save()

    WeeklyPlan.objects.filter(user=user).delete()

    return Response(_user_response(user, request), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_avatar(request):
    serializer = AvatarUploadSerializer(request.user, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.user.profile_picture:
        request.user.profile_picture.delete(save=False)

    user = serializer.save()
    return Response(_user_response(user, request), status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_avatar(request):
    if not request.user.profile_picture:
        return Response({"profile_picture_url": None}, status=status.HTTP_200_OK)

    return Response(
        {
            "profile_picture_url": request.build_absolute_uri(request.user.profile_picture.url)
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def google_login(request):
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

    base_username = email.split("@")[0]
    username = base_username
    counter = 1
    while CustomUser.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1

    user, created = CustomUser.objects.get_or_create(
        email=email,
        defaults={
            "username": username,
            "first_name": name,
        }
    )

    tokens = _tokens_for_user(user)

    return Response({
        "user": _user_response(user, request),
        "access": tokens["access"],
        "refresh": tokens["refresh"],
        "is_new_user": created,
    })