from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.db.models import DecimalField, F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin  # <--- IMPORTANTE

from .forms import ClienteForm, CreditoForm, PagoForm
from .models import Cliente, Credito, Cuota, Pago


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "creditos/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        inicio_mes = hoy.replace(day=1)

        total_creditos_activos = Credito.objects.exclude(
            estado=Credito.Estados.CANCELADO
        ).count()
        dinero_por_cobrar = (
            Cuota.objects.filter(
                estado__in=[Cuota.Estados.PENDIENTE, Cuota.Estados.PARCIAL]
            ).aggregate(
                total=Sum(
                    F("monto_programado") - F("monto_pagado"),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            )["total"]
            or Decimal("0.00")
        )
        pagos_del_dia = (
            Pago.objects.filter(fecha_pago=hoy).aggregate(total=Sum("monto"))["total"]
            or Decimal("0.00")
        )
        pagos_del_mes = (
            Pago.objects.filter(fecha_pago__gte=inicio_mes, fecha_pago__lte=hoy)
            .aggregate(total=Sum("monto"))
            .get("total")
            or Decimal("0.00")
        )
        clientes_en_mora = Cliente.objects.filter(
            creditos__cuotas__estado__in=[Cuota.Estados.PENDIENTE, Cuota.Estados.PARCIAL],
            creditos__cuotas__fecha_vencimiento__lt=hoy,
        ).distinct()

        cuotas_vencidas = (
            Cuota.objects.filter(estado__in=[Cuota.Estados.PENDIENTE, Cuota.Estados.PARCIAL])
            .filter(fecha_vencimiento__lt=hoy)
            .select_related("credito", "credito__cliente")
            .order_by("fecha_vencimiento")[:10]
        )

        context.update(
            {
                "total_creditos_activos": total_creditos_activos,
                "dinero_por_cobrar": dinero_por_cobrar,
                "pagos_del_dia": pagos_del_dia,
                "pagos_del_mes": pagos_del_mes,
                "clientes_en_mora": clientes_en_mora,
                "cuotas_vencidas": cuotas_vencidas,
            }
        )
        return context


class ClienteListView(LoginRequiredMixin, ListView):
    model = Cliente
    template_name = "creditos/clientes/lista.html"
    context_object_name = "clientes"
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()
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
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save()
            messages.success(request, "Cliente registrado correctamente.")
            return redirect("creditos:cliente_detalle", pk=cliente.pk)
        return render(request, self.template_name, {"form": form})


class ClienteUpdateView(LoginRequiredMixin, View):
    template_name = "creditos/clientes/formulario.html"

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        self.cliente = get_object_or_404(Cliente, pk=pk)
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
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, cliente_id):
        form = CreditoForm()
        return render(
            request,
            self.template_name,
            {"form": form, "cliente": self.cliente},
        )

    def post(self, request, cliente_id):
        form = CreditoForm(request.POST)
        if form.is_valid():
            credito = form.save(commit=False)
            credito.cliente = self.cliente
            credito.estado = Credito.Estados.ACTIVO
            credito.save()
            credito.generar_plan_pagos()
            messages.success(request, "Crédito creado correctamente.")
            return redirect("creditos:credito_detalle", pk=credito.pk)
        return render(
            request,
            self.template_name,
            {"form": form, "cliente": self.cliente},
        )


class CreditoDetailView(LoginRequiredMixin, DetailView):
    model = Credito
    template_name = "creditos/creditos/detalle.html"
    context_object_name = "credito"

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
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, credito_id):
        form = PagoForm(credito=self.credito)
        return render(
            request,
            self.template_name,
            {"form": form, "credito": self.credito},
        )

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
                return render(
                    request,
                    self.template_name,
                    {"form": form, "credito": self.credito},
                )
            messages.success(request, "Pago registrado correctamente.")
            return redirect("creditos:recibo_pago", pk=pago.pk)
        return render(
            request,
            self.template_name,
            {"form": form, "credito": self.credito},
        )


class ReciboPagoView(LoginRequiredMixin, DetailView):
    model = Pago
    template_name = "creditos/pagos/recibo.html"
    context_object_name = "pago"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["detalles"] = self.object.detalles.select_related("cuota")
        return context