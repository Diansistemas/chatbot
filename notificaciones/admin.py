from django.contrib import admin
from .models import Resumen

@admin.register(Resumen)
class ResumenAdmin(admin.ModelAdmin):
    search_fields = ("conversacion", "tipo")
    list_filter = ("tipo")