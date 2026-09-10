from django.urls import path
from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("chat/", views.chat_widget_view, name="chat"),
]