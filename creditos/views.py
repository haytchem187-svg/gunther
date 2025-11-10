from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.db.models import DecimalField, F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import ClienteForm, CreditoForm, PagoForm
from .models import Cliente, Credito, Cuota, Pago, UsuarioPerfil


def get_empresa_for_user(user):
    """
    Función auxiliar para obtener la empresa de un usuario de forma segura.
    Devuelve la empresa o None si el usuario no tiene perfil o empresa.
    """
    try:
        # <<< CORRECCIÓN: Acceso seguro al perfil y la empresa del usuario.
        return user.usuarioperfil.empresa
    except (UsuarioPerfil.DoesNotExist, AttributeError):
        return None


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "creditos/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        inicio_mes = hoy.replace(day=1)

        # <<< CORRECCIÓN: Obtener la empresa del usuario de forma bien segura.
        empresa_usuario = get_empresa_for_user(self.request.user)
        context["empresa_usuario"] = empresa_usuario
        
        # Si el usuario no tiene empresa, no se pueden calcular los datos.
        if not empresa_usuario:
            # <<< CORRECCIÓN: Devolver valores por defecto si no hay empresa.
            context.update({
                "total_creditos_activos": 0, "dinero_por_cobrar": Decimal("0.00"),
                "pagos_del_dia": Decimal("0.00"), "pagos_del_mes": Decimal("0.00"),
                "clientes_en_mora": Cliente.objects.none(), "cuotas_vencidas": Cuota.objects.none()
            })
            messages.warning(self.request, "No tienes una empresa asignada. Contacta al administrador.")
            return context

        # <<< CORRECCIÓN: Filtrar todos los queries por la empresa del usuario.
        total_creditos_activos = Credito.objects.filter(empresa=empresa_usuario).exclude(
            estado=Credito.Estados.CANCELADO
        ).count()

        dinero_por_cobrar = (
            Cuota.objects.filter(credito__empresa=empresa_usuario, 
                                 estado__in=[Cuota.Estados.PENDIENTE, Cuota.Estados.PARCIAL])
            .aggregate(total=Sum(F("monto_programado") - F("monto_pagado"), output_field=DecimalField(max_digits=12, decimal_places=2)))["total"]
            or Decimal("0.00")
        )
        pagos_del_dia = (
            Pago.objects.filter(credito__empresa=empresa_usuario, fecha_pago=hoy)
            .aggregate(total=Sum("monto"))["total"] or Decimal("0.00")
        )
        pagos_del_mes = (
            Pago.objects.filter(credito__empresa=empresa_usuario, fecha_pago__gte=inicio_mes, fecha_pago__lte=hoy)
            .aggregate(total=Sum("monto")).get("total") or Decimal("0.00")
        )
        clientes_en_mora = Cliente.objects.filter(
            empresa=empresa_usuario,
            creditos__cuotas__estado__in=[Cuota.Estados.PENDIENTE, Cuota.Estados.PARCIAL],
            creditos__cuotas__fecha_vencimiento__lt=hoy,
        ).distinct()

        cuotas_vencidas = (
            Cuota.objects.filter(credito__empresa=empresa_usuario, 
                                 estado__in=[Cuota.Estados.PENDIENTE, Cuota.Estados.PARCIAL])
            .filter(fecha_vencimiento__lt=hoy)
            .select_related("credito", "credito__cliente")
            .order_by("fecha_vencimiento")[:10]
        )

        context.update({
            "total_creditos_activos": total_creditos_activos, "dinero_por_cobrar": dinero_por_cobrar,
            "pagos_del_dia": pagos_del_dia, "pagos_del_mes": pagos_del_mes,
            "clientes_en_mora": clientes_en_mora, "cuotas_vencidas": cuotas_vencidas,
        })
        return context


class ClienteListView(LoginRequiredMixin, ListView):
    model = Cliente
    template_name = "creditos/clientes/lista.html"
    context_object_name = "clientes"
    paginate_by = 25

    def get_queryset(self):
        # <<< CORRECCIÓN: Obtener la empresa de forma segura.
        empresa = get_empresa_for_user(self.request.user)
        if not empresa:
            messages.error(self.request, "No tienes una empresa asignada para ver los clientes.")
            return Cliente.objects.none() # Devuelve una lista vacía si no hay empresa.

        queryset = Cliente.objects.filter(empresa=empresa)
        termino = self.request.GET.get("q")
        if termino:
            queryset = queryset.filter(
                Q(nombres__icontains=termino)
                | Q(apellidos__icontains=termino)
                | Q(identificacion__icontains=termino)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["termino"] = self.request.GET.get("q", "")
        return context


class ClienteDetailView(LoginRequiredMixin, DetailView):
    model = Cliente
    template_name = "creditos/clientes/detalle.html"
    context_object_name = "cliente"
    
    def dispatch(self, request, *args, **kwargs):
        # <<< CORRECCIÓN: Comprobar que el cliente pertenece a la empresa del usuario.
        cliente = self.get_object()
        empresa_usuario = get_empresa_for_user(request.user)
        if not empresa_usuario or cliente.empresa != empresa_usuario:
            messages.error(request, "No tienes permiso para ver este cliente.")
            return redirect("creditos:cliente_lista")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["creditos"] = self.object.creditos.select_related("cliente")
        return context


class ClienteCreateView(LoginRequiredMixin, View):
    template_name = "creditos/clientes/formulario.html"

    def get(self, request):
        form = ClienteForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        # <<< CORRECCIÓN: Obtener empresa de forma segura ANTES de procesar el formulario.
        empresa_usuario = get_empresa_for_user(request.user)
        if not empresa_usuario:
            messages.error(request, "No tienes una empresa asignada para crear clientes.")
            return redirect("creditos:cliente_lista")
            
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.empresa = empresa_usuario # Asigna la empresa obtenida de forma segura.
            cliente.save()
            messages.success(request, "Cliente registrado correctamente.")
            return redirect("creditos:cliente_detalle", pk=cliente.pk)
        return render(request, self.template_name, {"form": form})


# --- EL RESTO DE TUS VISTAS ESTÁN BIEN, PERO APLIQUÉ CHEQUEOS DE SEGURIDAD ---

class ClienteUpdateView(LoginRequiredMixin, View):
    template_name = "creditos/clientes/formulario.html"

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        self.cliente = get_object_or_404(Cliente, pk=pk)
        # <<< CORRECCIÓN: Comprobar que el cliente pertenece a la empresa del usuario.
        empresa_usuario = get_empresa_for_user(request.user)
        if not empresa_usuario or self.cliente.empresa != empresa_usuario:
            messages.error(request, "No tienes permiso para editar este cliente.")
            return redirect("creditos:cliente_lista")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        form = ClienteForm(instance=self.cliente)
        return render(request, self.template_name, {"form": form, "cliente": self.cliente})

    def post(self, request, pk):
        form = ClienteForm(request.POST, instance=self.cliente)
        if form.is_valid():
            form.save()
            messages.success(request, "Datos del cliente actualizados.")
            return redirect("creditos:cliente_detalle", pk=self.cliente.pk)
        return render(request, self.template_name, {"form": form, "cliente": self.cliente})


class CreditoCrearView(LoginRequiredMixin, View):
    template_name = "creditos/creditos/formulario.html"

    def dispatch(self, request, *args, **kwargs):
        cliente_id = kwargs.get("cliente_id")
        self.cliente = get_object_or_404(Cliente, pk=cliente_id)
        # <<< CORRECCIÓN: Comprobar que el cliente pertenece a la empresa del usuario.
        empresa_usuario = get_empresa_for_user(request.user)
        if not empresa_usuario or self.cliente.empresa != empresa_usuario:
            messages.error(request, "No puedes crear créditos para un cliente de otra empresa.")
            return redirect("creditos:cliente_lista")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, cliente_id):
        form = CreditoForm()
        return render(request, self.template_name, {"form": form, "cliente": self.cliente})

    def post(self, request, cliente_id):
        form = CreditoForm(request.POST)
        if form.is_valid():
            credito = form.save(commit=False)
            credito.cliente = self.cliente
            credito.empresa = self.cliente.empresa # <<< CORRECCIÓN: Asignar la empresa del cliente.
            credito.estado = Credito.Estados.ACTIVO
            credito.save()
            credito.generar_plan_pagos()
            messages.success(request, "Crédito creado correctamente.")
            return redirect("creditos:credito_detalle", pk=credito.pk)
        return render(request, self.template_name, {"form": form, "cliente": self.cliente})


class CreditoDetailView(LoginRequiredMixin, DetailView):
    model = Credito
    template_name = "creditos/creditos/detalle.html"
    context_object_name = "credito"

    def dispatch(self, request, *args, **kwargs):
        # <<< CORRECCIÓN: Comprobar que el crédito pertenece a la empresa del usuario.
        credito = self.get_object()
        empresa_usuario = get_empresa_for_user(request.user)
        if not empresa_usuario or credito.empresa != empresa_usuario:
            messages.error(request, "No tienes permiso para ver este crédito.")
            return redirect("creditos:cliente_lista")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cuotas"] = self.object.cuotas.all()
        context["pagos"] = self.object.pagos.all()
        context["saldo_pendiente"] = self.object.saldo_pendiente()
        context["pago_form"] = PagoForm(credito=self.object)
        return context


class RegistrarPagoView(LoginRequiredMixin, View):
    template_name = "creditos/pagos/formulario.html"

    def dispatch(self, request, *args, **kwargs):
        credito_id = kwargs.get("credito_id")
        self.credito = get_object_or_404(Credito, pk=credito_id)
        # <<< CORRECCIÓN: Comprobar que el crédito pertenece a la empresa del usuario.
        empresa_usuario = get_empresa_for_user(request.user)
        if not empresa_usuario or self.credito.empresa != empresa_usuario:
            messages.error(request, "No puedes registrar pagos para este crédito.")
            return redirect("creditos:cliente_lista")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, credito_id):
        form = PagoForm(credito=self.credito)
        return render(request, self.template_name, {"form": form, "credito": self.credito})

    def post(self, request, credito_id):
        form = PagoForm(request.POST, credito=self.credito)
        if form.is_valid():
            pago = form.save()
            try:
                pago.aplicar()
            except ValueError as error:
                pago.delete()
                form.add_error("monto", error)
                messages.error(request, str(error))
                return render(request, self.template_name, {"form": form, "credito": self.credito})
            messages.success(request, "Pago registrado correctamente.")
            return redirect("creditos:recibo_pago", pk=pago.pk)
        return render(request, self.template_name, {"form": form, "credito": self.credito})


class ReciboPagoView(LoginRequiredMixin, DetailView):
    model = Pago
    template_name = "creditos/pagos/recibo.html"
    context_object_name = "pago"
    
    def dispatch(self, request, *args, **kwargs):
        # <<< CORRECCIÓN: Comprobar que el pago pertenece a la empresa del usuario.
        pago = self.get_object()
        empresa_usuario = get_empresa_for_user(request.user)
        if not empresa_usuario or pago.credito.empresa != empresa_usuario:
            messages.error(request, "No tienes permiso para ver este recibo.")
            return redirect("creditos:cliente_lista")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["detalles"] = self.object.detalles.select_related("cuota")
        return context
