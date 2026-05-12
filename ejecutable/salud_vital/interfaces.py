from abc import ABC, abstractmethod
from typing import Any, Dict, List


class VariableAleatoria(ABC):
    @abstractmethod
    def muestrear(self) -> tuple[float, float]:
        """Devuelve el numero aleatorio y el valor generado."""


class InterfazSimulador(ABC):
    @abstractmethod
    def ejecutar(self) -> List[Dict[str, Any]]:
        """Ejecuta la simulacion y devuelve las filas visibles del estado."""
