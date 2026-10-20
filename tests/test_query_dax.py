from __future__ import annotations

from unittest.mock import patch
from server.tools.query_dax import normalize_dax_query, query_dax_model


def test_normalize_dax_query():
    # EVALUATE directo
    q1 = "EVALUATE TOPN(10, 'fact')"
    assert normalize_dax_query(q1) == q1

    # Expresión tabular sin EVALUATE
    q2 = "VALUES('fact'[nombre_promo])"
    assert normalize_dax_query(q2) == "EVALUATE\nVALUES('fact'[nombre_promo])"

    # Expresión escalar
    q3 = "SUM(fact[monto])"
    assert normalize_dax_query(q3) == "EVALUATE\nROW(\"Resultado\", SUM(fact[monto]))"

    # Medida directa
    q4 = "[Ventas Totales]"
    assert normalize_dax_query(q4) == "EVALUATE\nROW(\"Resultado\", [Ventas Totales])"


def test_query_dax_model_fails_gracefully_without_running_desktop():
    with patch("server.tools.query_dax.get_active_as_ports", return_value=[]):
        res = query_dax_model(dax_query="[Ventas]")
        assert res["success"] is False
        assert "No se encontró ninguna instancia activa" in res["error"]
