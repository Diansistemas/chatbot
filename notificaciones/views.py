from django.shortcuts import render
from django.db.models import Q
from django.views.generic import ListView, DetailView
from .models import Resumen

# Vistas de Resumen
class ResumenListView(ListView):
    model = Resumen
    template_name = ""
    context_object_name = "resumenes"

    def get_queryset(self):

        queryset = Resumen.objects.all().order_by("fecha_envio")
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(Q(conversacion__icontains=search) | Q(tipo__icontains=search))

        return queryset