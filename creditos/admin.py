from django.contrib import admin

from . import models


@admin.register(models.Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre_completo", "identificacion", "telefono", "email")
    search_fields = ("nombres", "apellidos", "identificacion")
    list_filter = ("fecha_registro",)


class CuotaInline(admin.TabularInline):
    model = models.Cuota
    extra = 0
    readonly_fields = (
        "numero",
        "fecha_vencimiento",
        "monto_programado",
        "monto_pagado",
        "estado",
    )


@admin.register(models.Credito)
class CreditoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cliente",
        "monto",
        "plazo_meses",
        "tasa_interes_anual",
        "estado",
    )
    search_fields = ("id", "cliente__nombres", "cliente__apellidos", "cliente__identificacion")
    list_filter = ("estado", "fecha_inicio")
    inlines = [CuotaInline]


class PagoDetalleInline(admin.TabularInline):
    model = models.PagoDetalle
    extra = 0
    readonly_fields = ("cuota", "monto_aplicado")


@admin.register(models.Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("credito", "fecha_pago", "monto", "metodo_pago")
    list_filter = ("fecha_pago",)
    search_fields = ("credito__cliente__nombres", "credito__cliente__apellidos", "credito__cliente__identificacion")
    inlines = [PagoDetalleInline]
