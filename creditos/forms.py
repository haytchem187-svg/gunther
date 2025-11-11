from __future__ import annotations

from decimal import Decimal

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Cliente, Credito, Empresa, Pago, UsuarioPerfil


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


class BaseUsuarioForm(forms.ModelForm):
    empresa = forms.ModelChoiceField(
        label="Empresa",
        queryset=Empresa.objects.filter(activa=True).order_by("nombre"),
        required=False,
        help_text="Asocia el usuario a una empresa activa.",
    )

    def _aplicar_clases_css(self) -> None:
        for field in self.fields.values():
            classes = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"form-control {classes}".strip()

    def guardar_perfil(self, user: User) -> UsuarioPerfil:
        empresa = self.cleaned_data.get("empresa")
        perfil, _ = UsuarioPerfil.objects.get_or_create(user=user)
        perfil.empresa = empresa
        perfil.save()
        return perfil


class UsuarioCrearForm(UserCreationForm, BaseUsuarioForm):
    email = forms.EmailField(label="Correo electrónico", required=False)
    first_name = forms.CharField(label="Nombre", max_length=150, required=False)
    last_name = forms.CharField(label="Apellidos", max_length=150, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._aplicar_clases_css()
        # Campos de contraseña requieren clases manuales
        self.fields["password1"].widget.attrs["class"] = "form-control"
        self.fields["password2"].widget.attrs["class"] = "form-control"

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.email = self.cleaned_data.get("email", "")
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        if commit:
            user.save()
            self.guardar_perfil(user)
        return user


class UsuarioActualizarForm(BaseUsuarioForm):
    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "is_staff",
        )
        help_texts = {
            "is_staff": "Permite el acceso al panel de administración.",
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        perfil = None
        if self.instance.pk:
            try:
                perfil = self.instance.usuarioperfil
            except UsuarioPerfil.DoesNotExist:
                perfil = None
        if perfil and "empresa" in self.fields:
            self.fields["empresa"].initial = perfil.empresa
        self._aplicar_clases_css()

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=commit)
        self.guardar_perfil(user)
        return user
