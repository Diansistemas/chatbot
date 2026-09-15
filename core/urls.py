from django.urls import path
from . import views

urlpatterns = [
    path("", views.InicioView.as_view(), name="inicio"),
    path("chat/", views.ChatWidgetView.as_view(), name="chat"),
]