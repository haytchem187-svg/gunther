from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Cliente, Credito, Cuota, Pago


class ClienteModelTest(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nombres="Juan",
            apellidos="Pérez",
            identificacion="1234567890",
            telefono="3001234567",
            email="juan@example.com",
        )

    def test_cliente_str(self):
        """Test que el método __str__ retorna el nombre completo"""
        self.assertEqual(str(self.cliente), "Juan Pérez")

    def test_nombre_completo(self):
        """Test que la propiedad nombre_completo funciona"""
        self.assertEqual(self.cliente.nombre_completo, "Juan Pérez")

    def test_saldo_total_sin_creditos(self):
        """Test que saldo_total es 0 cuando no hay créditos"""
        self.assertEqual(self.cliente.saldo_total(), Decimal("0.00"))


class CreditoModelTest(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nombres="María",
            apellidos="García",
            identificacion="9876543210",
        )
        self.credito = Credito.objects.create(
            cliente=self.cliente,
            monto=Decimal("1000000.00"),
            plazo_meses=12,
            tasa_interes_anual=Decimal("12.00"),
            fecha_inicio=timezone.localdate(),
        )

    def test_credito_str(self):
        """Test que el método __str__ funciona"""
        self.assertIn("Crédito", str(self.credito))
        self.assertIn("María García", str(self.credito))

    def test_tasa_mensual(self):
        """Test que la tasa mensual se calcula correctamente"""
        expected = Decimal("0.01")
        self.assertEqual(self.credito.tasa_mensual, expected)

    def test_generar_plan_pagos(self):
        """Test que se genera el plan de pagos correctamente"""
        self.credito.generar_plan_pagos()
        cuotas = self.credito.cuotas.all()
        self.assertEqual(cuotas.count(), 12)
        self.assertEqual(cuotas.first().numero, 1)
        self.assertEqual(cuotas.last().numero, 12)

    def test_saldo_pendiente_completo(self):
        """Test que el saldo pendiente es el total cuando no se ha pagado"""
        self.credito.generar_plan_pagos()
        saldo = self.credito.saldo_pendiente()
        total_programado = sum(c.monto_programado for c in self.credito.cuotas.all())
        self.assertEqual(saldo, total_programado)


class PagoModelTest(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nombres="Carlos",
            apellidos="López",
            identificacion="5555555555",
        )
        self.credito = Credito.objects.create(
            cliente=self.cliente,
            monto=Decimal("500000.00"),
            plazo_meses=6,
            tasa_interes_anual=Decimal("10.00"),
            fecha_inicio=timezone.localdate(),
        )
        self.credito.generar_plan_pagos()

    def test_aplicar_pago_primera_cuota(self):
        """Test que aplicar un pago funciona correctamente"""
        primera_cuota = self.credito.cuotas.first()
        monto_cuota = primera_cuota.monto_programado
        
        pago = Pago.objects.create(
            credito=self.credito,
            monto=monto_cuota,
            fecha_pago=timezone.localdate(),
        )
        pago.aplicar()
        
        primera_cuota.refresh_from_db()
        self.assertEqual(primera_cuota.estado, Cuota.Estados.PAGADA)
        self.assertEqual(primera_cuota.monto_pagado, monto_cuota)


class DashboardViewTest(TestCase):
    def test_dashboard_view(self):
        """Test que la vista del dashboard carga correctamente"""
        response = self.client.get(reverse("creditos:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "creditos/dashboard.html")


class ClienteViewsTest(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nombres="Ana",
            apellidos="Martínez",
            identificacion="1111111111",
        )

    def test_cliente_list_view(self):
        """Test que la lista de clientes carga correctamente"""
        response = self.client.get(reverse("creditos:clientes_lista"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ana Martínez")

    def test_cliente_detail_view(self):
        """Test que el detalle de cliente carga correctamente"""
        response = self.client.get(
            reverse("creditos:cliente_detalle", kwargs={"pk": self.cliente.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ana Martínez")
