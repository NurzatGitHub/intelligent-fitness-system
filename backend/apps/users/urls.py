from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login, name="login"),
    path("me/", views.me, name="me"),
    path("me/avatar/", views.upload_avatar, name="upload-avatar"),
    path("me/avatar/url/", views.my_avatar, name="my-avatar-url"),
    path("google/", views.google_login, name="google_login"),
]