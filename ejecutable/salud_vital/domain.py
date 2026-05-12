from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# Objetos del dominio del sistema de simulación de vacunación.
# Aca vamos a definir las entidades principales: personas, puestos de vacunación, eventos y estadísticas.

# Esta clase representa los estados posibles de los puestos de vacunacion 1 y 2
class EstadoPuesto(str, Enum):
    LIBRE = "Libre" # No tiene personas en la cola
    OCUPADO = "Ocupado" # Esta vacunando a alguien
    BLOQUEADO = "Bloqueado" # La zona de observacione esta llena

# Representa a una persona que se mueve por el sistema de vacunacion
@dataclass
class Persona:
    id_persona: int # Identificador de la persona
    tiempo_llegada: float # Momento en el que la persona llega al sistema
    inicio_vacunacion: Optional[float] = None # Momento en el que la empiezan a vacunar
    fin_vacunacion: Optional[float] = None # Momento en el que la terminan de vacunar (es None si no lo hicieron)
    fin_observacion: Optional[float] = None # Momento en el que termina la observacion (es None si no termino)

# Representa a un puesto de vacunacion con estados 
@dataclass
class PuestoVacunacion:
    nombre: str # Identificador unico del puesto
    estado: EstadoPuesto = EstadoPuesto.LIBRE # Estado actual (por defecto libre)
    persona_actual: Optional[Persona] = None # Persona a la que se esta atendiendo ahora (None si esta libre)
    proximo_fin_tiempo: Optional[float] = None # Hora del fin de vacunacion actual (None si esta libre)
    tiempo_inicio_bloqueo: Optional[float] = None # Momento en que se bloqueo (None si estado no es Bloqueado)
    tiempo_bloqueo_acumulado: float = 0.0 # Total de minutos que el puesto ha estado bloqueado
    ultimo_rnd_vacunacion: Optional[float] = None # Ultimo RND aleatorio usado para tiempo de vacunacion
    ultimo_tiempo_vacunacion: Optional[float] = None # Ultima duracion de vacunacion generada

    def esta_libre(self) -> bool:
        # Verifica si el puesto esta disponible para atender
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
