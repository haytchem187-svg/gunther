from __future__ import annotations

import calendar
from datetime import date


def sumar_meses(fecha: date, meses: int) -> date:
    """Retorna una nueva fecha sumando *meses* a *fecha*."""
    mes = fecha.month - 1 + meses
    anio = fecha.year + mes // 12
    mes = mes % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)
