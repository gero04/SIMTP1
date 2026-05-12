import math
import random
from dataclasses import dataclass

from .interfaces import VariableAleatoria


@dataclass
class ExponencialNegativa(VariableAleatoria):
    media: float

    def muestrear(self) -> tuple[float, float]:
        rnd = random.random()
        valor = -self.media * math.log(1 - rnd)
        return rnd, valor


@dataclass
class Uniforme(VariableAleatoria):
    minimo: float
    maximo: float

    def muestrear(self) -> tuple[float, float]:
        rnd = random.random()
        valor = self.minimo + rnd * (self.maximo - self.minimo)
        return rnd, valor
