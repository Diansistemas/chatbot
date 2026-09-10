from django.shortcuts import render
from django.db.models import Q
from django.views.generic import ListView, DetailView
from .models import Servicio

# Vistas de Servicio
class ServicioListView(ListView):
    model = Servicio
    template_name = ""
    context_object_name = "servicios"

    def get_queryset(self):

        queryset = Servicio.objects.all().order_by("fecha_envio")
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(Q(nombre__icontains=search) | Q(descripcion__icontains=search) | Q(coste__icontains=search) | Q(tiempo_aproximado__icontains=search))

        return queryset