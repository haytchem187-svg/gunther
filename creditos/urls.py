from django.urls import path

from . import views

app_name = "creditos"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("clientes/", views.ClienteListView.as_view(), name="clientes_lista"),
    path("clientes/nuevo/", views.ClienteCreateView.as_view(), name="cliente_nuevo"),
    path("clientes/<int:pk>/", views.ClienteDetailView.as_view(), name="cliente_detalle"),
    path(
        "clientes/<int:pk>/editar/",
        views.ClienteUpdateView.as_view(),
        name="cliente_editar",
    ),
    path(
        "clientes/<int:cliente_id>/creditos/nuevo/",
        views.CreditoCrearView.as_view(),
        name="credito_nuevo",
    ),
    path("creditos/<int:pk>/", views.CreditoDetailView.as_view(), name="credito_detalle"),
    path(
        "creditos/<int:credito_id>/pagos/nuevo/",
        views.RegistrarPagoView.as_view(),
        name="pago_nuevo",
    ),
    path("pagos/<int:pk>/recibo/", views.ReciboPagoView.as_view(), name="recibo_pago"),
    path("usuarios/", views.UsuarioListView.as_view(), name="usuarios_lista"),
    path("usuarios/nuevo/", views.UsuarioCreateView.as_view(), name="usuarios_nuevo"),
    path("usuarios/<int:pk>/editar/", views.UsuarioUpdateView.as_view(), name="usuarios_editar"),
]
