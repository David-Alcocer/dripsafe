"""Pruebas del balance físico simplificado de una torre."""

import math

import pytest

from src.metricas.purga import balance_torre


def test_cuatro_ciclos_cierran_el_balance_de_masa():
    balance = balance_torre(3.0, 4.0)
    assert balance == {"evaporacion_l": 3.0, "purga_l": 1.0, "reposicion_l": 4.0}
    assert balance["reposicion_l"] / balance["purga_l"] == 4.0


def test_mas_ciclos_reducen_purga_a_igual_evaporacion():
    assert balance_torre(12, 6)["purga_l"] < balance_torre(12, 3)["purga_l"]


@pytest.mark.parametrize("evaporacion,ciclos", [(-1, 4), (1, 1), (1, 0),
                                                  (math.nan, 4), (1, math.inf),
                                                  (True, 4)])
def test_entradas_invalidas_se_rechazan(evaporacion, ciclos):
    with pytest.raises(ValueError):
        balance_torre(evaporacion, ciclos)
