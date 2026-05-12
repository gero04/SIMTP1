from dataclasses import dataclass


@dataclass
class ConfiguracionSimulacion:
    tiempo_simulacion: float
    maximo_iteraciones: int = 100000
    mostrar_desde_tiempo: float = 0.0
    filas_a_mostrar: int = 100
    media_llegada: float = 6.0
    vacunacion_minima: float = 3.0
    vacunacion_maxima: float = 7.0
    tiempo_observacion: float = 15.0
    capacidad_observacion: int = 20
    maximo_cola_antes_rechazo: int = 10
    seed: int | None = None
