from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import F, Sum
from django.utils import timezone

from django.contrib.auth.models import User
from . import utils


# --- NUEVO MODELO Empresa ---
class Empresa(models.Model):
    nombre = models.CharField(max_length=200, unique=True)
    contacto = models.CharField(max_length=200, blank=True)
    activa = models.BooleanField(default=True)
    fecha_registro = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.nombre


# --- PERFIL DE USUARIO (vincula usuario a empresa) ---
class UsuarioPerfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # 🔸 Cambio clave: ahora la empresa puede ser opcional
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.SET_NULL,   # Si la empresa se elimina, no borra el usuario
        null=True,                   # Permite nulos (usuarios sin empresa)
        blank=True                   # Campo opcional en formularios/admin
    )

    def __str__(self):
        if self.empresa:
            return f"{self.user.username} - {self.empresa.nombre}"
        return f"{self.user.username} (sin empresa)"


# --- MODIFICADO: Relación empresa en Cliente ---
class Cliente(models.Model):
    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, related_name="clientes"
    )
    nombres = models.CharField("Nombres", max_length=150)
    apellidos = models.CharField("Apellidos", max_length=150, blank=True)
    identificacion = models.CharField(
        "Número de identificación", max_length=50
    )
    telefono = models.CharField("Teléfono", max_length=30, blank=True)
    email = models.EmailField("Correo electrónico", blank=True)
    direccion = models.CharField("Dirección", max_length=255, blank=True)
    fecha_registro = models.DateField("Fecha de registro", auto_now_add=True)

    class Meta:
        ordering = ["nombres", "apellidos"]
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        unique_together = ("empresa", "identificacion")

    def __str__(self) -> str:
        if self.apellidos:
            return f"{self.nombres} {self.apellidos}".strip()
        return self.nombres

    @property
    def nombre_completo(self) -> str:
        return str(self)

    def saldo_total(self) -> Decimal:
        total = Decimal("0.00")
        for credito in self.creditos.all():
            total += credito.saldo_pendiente()
        return total


class Credito(models.Model):
    class Estados(models.TextChoices):
        ACTIVO = "activo", "Activo"
        CANCELADO = "cancelado", "Cancelado"
        EN_MORA = "en_mora", "En mora"

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="creditos",
    )
    cliente = models.ForeignKey(
        Cliente, on_delete=models.CASCADE, related_name="creditos"
    )
    monto = models.DecimalField(
        "Monto del crédito",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    plazo_meses = models.PositiveIntegerField("Plazo (meses)")
    tasa_interes_anual = models.DecimalField(
        "Tasa de interés anual (%)",
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    fecha_inicio = models.DateField("Fecha de inicio", default=timezone.localdate)
    estado = models.CharField(
        "Estado",
        max_length=20,
        choices=Estados.choices,
        default=Estados.ACTIVO,
    )
    notas = models.TextField("Notas", blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Crédito"
        verbose_name_plural = "Créditos"

    def __str__(self) -> str:
        return f"Crédito #{self.id} - {self.cliente.nombre_completo}"

    def save(self, *args, **kwargs):
        if self.cliente_id and (self.empresa_id is None or self.empresa_id != self.cliente.empresa_id):
            self.empresa = self.cliente.empresa
        super().save(*args, **kwargs)

    @property
    def tasa_mensual(self) -> Decimal:
        return (self.tasa_interes_anual / Decimal("100")) / Decimal("12")

    def pago_mensual_estimado(self) -> Decimal:
        tasa = self.tasa_mensual
        meses = self.plazo_meses
        if meses == 0:
            return Decimal("0.00")
        if tasa == 0:
            return (self.monto / meses).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        factor = (Decimal("1") + tasa) ** meses
        pago = self.monto * tasa * factor / (factor - Decimal("1"))
        return pago.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def generar_plan_pagos(self) -> None:
        self.cuotas.all().delete()
        tasa = self.tasa_mensual
        meses = self.plazo_meses
        pago_mensual = self.pago_mensual_estimado()
        saldo = self.monto

        for numero in range(1, meses + 1):
            interes = (saldo * tasa).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if tasa == 0:
                capital = (self.monto / meses).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                interes = Decimal("0.00")
            else:
                capital = (pago_mensual - interes).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

            if numero == meses:
                capital = saldo
                pago = (capital + interes).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                pago = (capital + interes).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            fecha_vencimiento = utils.sumar_meses(self.fecha_inicio, numero - 1)

            self.cuotas.create(
                numero=numero,
                fecha_vencimiento=fecha_vencimiento,
                monto_programado=pago,
                interes_programado=interes,
                capital_programado=capital,
            )
            saldo = (saldo - capital).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if saldo < Decimal("0.01"):
                saldo = Decimal("0.00")

        self.actualizar_estado()

    def cuotas_pendientes(self) -> Iterable["Cuota"]:
        return self.cuotas.filter(
            estado__in=[Cuota.Estados.PENDIENTE, Cuota.Estados.PARCIAL]
        ).order_by("numero")

    def saldo_pendiente(self) -> Decimal:
        total = self.cuotas.annotate(
            restante=F("monto_programado") - F("monto_pagado")
        ).aggregate(
            total=Sum(
                "restante",
                output_field=models.DecimalField(max_digits=12, decimal_places=2),
            )
        )
        return total["total"] or Decimal("0.00")

    def total_pagado(self) -> Decimal:
        total = self.cuotas.aggregate(total=Sum("monto_pagado"))
        return total["total"] or Decimal("0.00")

    def actualizar_estado(self) -> None:
        pendientes = self.cuotas.filter(
            estado__in=[Cuota.Estados.PENDIENTE, Cuota.Estados.PARCIAL]
        )
        if not pendientes.exists():
            self.estado = self.Estados.CANCELADO
        elif pendientes.filter(fecha_vencimiento__lt=timezone.localdate()).exists():
            self.estado = self.Estados.EN_MORA
        else:
            self.estado = self.Estados.ACTIVO
        self.save(update_fields=["estado", "actualizado_en"])


class Cuota(models.Model):
    class Estados(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        PARCIAL = "parcial", "Parcial"
        PAGADA = "pagada", "Pagada"

    credito = models.ForeignKey(
        Credito, on_delete=models.CASCADE, related_name="cuotas"
    )
    numero = models.PositiveIntegerField("Número de cuota")
    fecha_vencimiento = models.DateField("Fecha de vencimiento")
    monto_programado = models.DecimalField(
        "Monto programado",
        max_digits=12,
        decimal_places=2,
    )
    interes_programado = models.DecimalField(
        "Interés programado",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    capital_programado = models.DecimalField(
        "Capital programado",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    monto_pagado = models.DecimalField(
        "Monto pagado",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    estado = models.CharField(
        "Estado",
        max_length=20,
        choices=Estados.choices,
        default=Estados.PENDIENTE,
    )
    fecha_pago = models.DateField("Fecha de pago", blank=True, null=True)

    class Meta:
        ordering = ["numero"]
        verbose_name = "Cuota"
        verbose_name_plural = "Cuotas"
        unique_together = ("credito", "numero")

    def __str__(self) -> str:
        return f"Cuota {self.numero}"

    @property
    def saldo(self) -> Decimal:
        return (self.monto_programado - self.monto_pagado).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @property
    def vencida(self) -> bool:
        return self.estado != self.Estados.PAGADA and self.fecha_vencimiento < timezone.localdate()


class Pago(models.Model):
    credito = models.ForeignKey(
        Credito, on_delete=models.CASCADE, related_name="pagos"
    )
    fecha_pago = models.DateField("Fecha de pago", default=timezone.localdate)
    monto = models.DecimalField(
        "Monto pagado",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    metodo_pago = models.CharField("Método de pago", max_length=50, blank=True)
    referencia = models.CharField("Referencia", max_length=100, blank=True)
    notas = models.TextField("Notas", blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"

    def __str__(self) -> str:
        return f"Pago {self.monto} - {self.credito}"

    def aplicar(self) -> None:
        saldo = self.monto
        cuotas = self.credito.cuotas_pendientes()
        with transaction.atomic():
            for cuota in cuotas:
                if saldo <= 0:
                    break
                restante = cuota.monto_programado - cuota.monto_pagado
                aplicado = min(restante, saldo)
                PagoDetalle.objects.create(
                    pago=self,
                    cuota=cuota,
                    monto_aplicado=aplicado,
                )
                cuota.monto_pagado = (cuota.monto_pagado + aplicado).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                if cuota.monto_pagado >= cuota.monto_programado:
                    cuota.estado = Cuota.Estados.PAGADA
                    cuota.fecha_pago = self.fecha_pago
                else:
                    cuota.estado = Cuota.Estados.PARCIAL
                cuota.save()
                saldo -= aplicado

            if saldo > 0:
                raise ValueError("El monto excede el saldo pendiente del crédito.")

            self.credito.actualizar_estado()

    def total_aplicado(self) -> Decimal:
        total = self.detalles.aggregate(total=Sum("monto_aplicado"))
        return total["total"] or Decimal("0.00")


class PagoDetalle(models.Model):
    pago = models.ForeignKey(
        Pago, on_delete=models.CASCADE, related_name="detalles"
    )
    cuota = models.ForeignKey(
        Cuota, on_delete=models.CASCADE, related_name="pagos_detalle"
    )
    monto_aplicado = models.DecimalField(
        "Monto aplicado",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    class Meta:
        verbose_name = "Detalle de pago"
        verbose_name_plural = "Detalles de pago"

    def __str__(self) -> str:
        return f"{self.monto_aplicado} a {self.cuota}"
