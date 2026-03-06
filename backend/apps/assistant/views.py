import os

from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import UserRateThrottle

from google import genai


class AssistantChatThrottle(UserRateThrottle):
    scope = "assistant_chat"


def build_system_prompt(user) -> str:
    return (
        "You are a fitness coach inside a mobile app. "
        "Answer briefly, clearly, and practically. "
        "Use the user's fitness profile to personalize the answer. "
        "If the user mentions pain or injury, advise them to stop and consult a professional. "
        "Do not give medical diagnosis.\n\n"
        f"User profile:\n"
        f"- fitness level: {getattr(user, 'fitness_level', '')}\n"
        f"- goal: {getattr(user, 'goal', '')}\n"
        f"- limitations: {getattr(user, 'limitations', '')}\n"
        f"- training frequency per week: {getattr(user, 'frequency', '')}\n"
    )


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
    max_out = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "450"))

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