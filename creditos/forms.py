from __future__ import annotations

from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Cliente, Credito, Pago


class ClienteForm(forms.ModelForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"form-control {css_class}".strip()

    class Meta:
        model = Cliente
        fields = (
            "nombres",
            "apellidos",
            "identificacion",
            "telefono",
            "email",
            "direccion",
        )
        widgets = {
            "direccion": forms.Textarea(attrs={"rows": 2}),
        }


class CreditoForm(forms.ModelForm):
    fecha_inicio = forms.DateField(
        label="Fecha de inicio",
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = Credito
        fields = (
            "monto",
            "plazo_meses",
            "tasa_interes_anual",
            "fecha_inicio",
            "notas",
        )
        widgets = {
            "notas": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            classes = widget.attrs.get("class", "")
            widget.attrs["class"] = f"form-control {classes}".strip()


class PagoForm(forms.ModelForm):
    fecha_pago = forms.DateField(
        label="Fecha de pago",
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = Pago
        fields = ("fecha_pago", "monto", "metodo_pago", "referencia", "notas")
        widgets = {
            "notas": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, credito: Credito, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.credito = credito
        self.fields["monto"].widget.attrs["min"] = "0.01"
        self.fields["monto"].widget.attrs["step"] = "0.01"
        for field in self.fields.values():
            classes = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"form-control {classes}".strip()

    def clean_monto(self) -> Decimal:
        monto = self.cleaned_data["monto"]
        saldo = self.credito.saldo_pendiente()
        if monto <= 0:
            raise ValidationError("El monto debe ser mayor a cero.")
        if monto > saldo:
            raise ValidationError(
                "El monto supera el saldo pendiente del crédito ({}).".format(saldo)
            )
        return monto

    def save(self, commit: bool = True) -> Pago:
        pago = super().save(commit=False)
        pago.credito = self.credito
        if commit:
            pago.save()
        return pago
