from __future__ import annotations

from typing import Dict, Optional

from django.http import HttpRequest

from .models import UsuarioPerfil


def empresa_actual(request: HttpRequest) -> Dict[str, Optional[str]]:
    """Agrega la empresa asociada al usuario autenticado al contexto."""
    empresa_nombre: Optional[str] = None

    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        perfil = getattr(user, "usuarioperfil", None)
        if isinstance(perfil, UsuarioPerfil) and perfil.empresa and perfil.empresa.activa:
            empresa_nombre = perfil.empresa.nombre

    return {"empresa_actual": empresa_nombre}
