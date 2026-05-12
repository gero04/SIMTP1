from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EstadoPuesto(str, Enum):
    LIBRE = "Libre"
    OCUPADO = "Ocupado"
    BLOQUEADO = "Bloqueado"


@dataclass
class Persona:
    id_persona: int
    tiempo_llegada: float
    inicio_vacunacion: Optional[float] = None
    fin_vacunacion: Optional[float] = None
    fin_observacion: Optional[float] = None


@dataclass
class PuestoVacunacion:
    nombre: str
    estado: EstadoPuesto = EstadoPuesto.LIBRE
    persona_actual: Optional[Persona] = None
    proximo_fin_tiempo: Optional[float] = None
    tiempo_inicio_bloqueo: Optional[float] = None
    tiempo_bloqueo_acumulado: float = 0.0
    ultimo_rnd_vacunacion: Optional[float] = None
    ultimo_tiempo_vacunacion: Optional[float] = None

    def esta_libre(self) -> bool:
        return self.estado == EstadoPuesto.LIBRE

    def iniciar_vacunacion(self, persona: Persona, reloj: float, rnd: float, duracion: float) -> None:
        persona.inicio_vacunacion = reloj
        persona.fin_vacunacion = reloj + duracion
        self.persona_actual = persona
        self.estado = EstadoPuesto.OCUPADO
        self.proximo_fin_tiempo = persona.fin_vacunacion
        self.ultimo_rnd_vacunacion = rnd
        self.ultimo_tiempo_vacunacion = duracion

    def bloquear(self, reloj: float) -> None:
        self.estado = EstadoPuesto.BLOQUEADO
        self.tiempo_inicio_bloqueo = reloj
        self.proximo_fin_tiempo = None

    def liberar_de_bloqueo(self, reloj: float) -> Optional[Persona]:
        if self.tiempo_inicio_bloqueo is not None:
            self.tiempo_bloqueo_acumulado += reloj - self.tiempo_inicio_bloqueo
        persona = self.persona_actual
        self.persona_actual = None
        self.tiempo_inicio_bloqueo = None
        self.estado = EstadoPuesto.LIBRE
        self.proximo_fin_tiempo = None
        return persona

    def finalizar_sin_bloqueo(self) -> Optional[Persona]:
        persona = self.persona_actual
        self.persona_actual = None
        self.estado = EstadoPuesto.LIBRE
        self.proximo_fin_tiempo = None
        return persona


@dataclass(order=True)
class EventoProgramado:
    time: float
    priority: int
    tipo_evento: str = field(compare=False)
    carga_util: object = field(compare=False, default=None)


@dataclass
class EstadisticasSimulacion:
    llegadas: int = 0
    rechazadas: int = 0
    completadas: int = 0
    permanencia_acumulada: float = 0.0

    @property
    def porcentaje_rechazo(self) -> float:
        if self.llegadas == 0:
            return 0.0
        return (self.rechazadas / self.llegadas) * 100

    @property
    def permanencia_promedio(self) -> float:
        if self.completadas == 0:
            return 0.0
        return self.permanencia_acumulada / self.completadas
