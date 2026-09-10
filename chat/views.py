from django.shortcuts import render
from django.db.models import Q
from django.views.generic import ListView, DetailView
from .models import Conversacion, Mensaje

# Vistas de Conversacion
class ConversacionListView(ListView):
    model = Conversacion
    template_name = ""
    context_object_name = "conversaciones"

    def get_queryset(self):

        queryset = Conversacion.objects.all().order_by("fecha_inicio")
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(Q(fecha_inicio__icontains=search) | Q(estado__icontains=search) | Q(tipo__icontains=search))

        return queryset


# Vistas de Mensajes
class MensajesListView(ListView):
    model = Mensaje
    template_name = ""
    context_object_name = "mensajes"

    def get_queryset(self):

        queryset = Mensaje.objects.all().order_by("fecha_mensaje")
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(Q(texto__icontains=search) | Q(remitente__icontains=search) | Q(conversacion__icontais=search))

        return queryset