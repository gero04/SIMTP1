from collections import deque
import heapq
import random
from typing import Any, Deque, Dict, List, Optional

from .config import ConfiguracionSimulacion
from .domain import EstadisticasSimulacion, EstadoPuesto, EventoProgramado, Persona, PuestoVacunacion
from .interfaces import InterfazSimulador
from .random_variables import ExponencialNegativa, Uniforme


class SimuladorCentroVacunacion(InterfazSimulador):
    LLEGADA = "Llegada"
    FIN_VACUNACION = "Fin vacunacion"
    FIN_OBSERVACION = "Fin observacion"
    FIN_SIMULACION = "Fin simulacion"

    def __init__(self, configuracion: ConfiguracionSimulacion) -> None:
        self.configuracion = configuracion
        if configuracion.seed is not None:
            random.seed(configuracion.seed)

        self.variable_llegada = ExponencialNegativa(configuracion.media_llegada)
        self.variable_vacunacion = Uniforme(configuracion.vacunacion_minima, configuracion.vacunacion_maxima)

        self.reloj = 0.0
        self.iteracion = 0
        self.proximo_id_persona = 1
        self.estadisticas = EstadisticasSimulacion()
        self.cola: Deque[Persona] = deque()
        self.puestos = [PuestoVacunacion("P1"), PuestoVacunacion("P2")]
        self.observacion: dict[int, tuple[float, Persona]] = {}
        self.eventos: list[EventoProgramado] = []

        self.fila_actual: Optional[Dict[str, Any]] = None
        self.fila_anterior: Optional[Dict[str, Any]] = None
        self.filas_visibles: List[Dict[str, Any]] = []
        self.fila_final: Optional[Dict[str, Any]] = None
        self.max_objetos_visibles = 0
        self.persona_evento_actual: Optional[Persona] = None
        self.estado_evento_actual: Optional[str] = None
        self.ultimo_rnd_llegada: Optional[float] = None
        self.ultimo_tiempo_entre_llegadas: Optional[float] = None
        self.vacunaciones_por_puesto: Dict[str, int] = {"P1": 0, "P2": 0}
        self.ultimos_aleatorios_evento: Dict[str, Optional[float]] = {
            "rnd_llegada": None,
            "t_entre_llegadas": None,
            "rnd_vac_p1": None,
            "t_vac_p1": None,
            "rnd_vac_p2": None,
            "t_vac_p2": None,
        }

    def ejecutar(self) -> List[Dict[str, Any]]:
        self._programar_primera_llegada()

        while self.eventos and self.iteracion < min(self.configuracion.maximo_iteraciones, 100000):
            evento = heapq.heappop(self.eventos)
            if evento.time > self.configuracion.tiempo_simulacion:
                break
            self.reloj = evento.time
            self.iteracion += 1
            self._reiniciar_ultimos_aleatorios_evento()
            self._despachar(evento)
            self._tomar_snapshot(evento.tipo_evento)

        self.reloj = self.configuracion.tiempo_simulacion
        self._cerrar_bloqueos_abiertos()
        self._tomar_snapshot(self.FIN_SIMULACION, forzar_final=True)
        self._normalizar_columnas_objetos()
        self._destruir_objetos_de_ejecucion()
        return self.filas_visibles

    def obtener_resumen(self) -> Dict[str, float]:
        bloqueo_total = sum(puesto.tiempo_bloqueo_acumulado for puesto in self.puestos)
        return {
            "personas_llegadas": self.estadisticas.llegadas,
            "personas_rechazadas": self.estadisticas.rechazadas,
            "personas_completadas": self.estadisticas.completadas,
            "porcentaje_rechazo": self.estadisticas.porcentaje_rechazo,
            "bloqueo_promedio_puestos": bloqueo_total / len(self.puestos),
            "bloqueo_p1": self.puestos[0].tiempo_bloqueo_acumulado,
            "bloqueo_p2": self.puestos[1].tiempo_bloqueo_acumulado,
            "vacunaciones_p1": self.vacunaciones_por_puesto["P1"],
            "vacunaciones_p2": self.vacunaciones_por_puesto["P2"],
            "permanencia_promedio": self.estadisticas.permanencia_promedio,
        }

    def _programar_primera_llegada(self) -> None:
        rnd, tiempo_entre_llegadas = self.variable_llegada.muestrear()
        self.ultimo_rnd_llegada = rnd
        self.ultimo_tiempo_entre_llegadas = tiempo_entre_llegadas
        self._agregar_evento(tiempo_entre_llegadas, 1, self.LLEGADA)

    def _despachar(self, evento: EventoProgramado) -> None:
        if evento.tipo_evento == self.LLEGADA:
            self._manejar_llegada()
        elif evento.tipo_evento == self.FIN_VACUNACION:
            self._manejar_fin_vacunacion(evento.carga_util)
        elif evento.tipo_evento == self.FIN_OBSERVACION:
            self._manejar_fin_observacion(evento.carga_util)

    def _manejar_llegada(self) -> None:
        persona = Persona(self.proximo_id_persona, self.reloj)
        self.proximo_id_persona += 1
        self.estadisticas.llegadas += 1
        self.persona_evento_actual = persona
        self.estado_evento_actual = "Llegada"

        rnd, tiempo_entre_llegadas = self.variable_llegada.muestrear()
        self.ultimo_rnd_llegada = rnd
        self.ultimo_tiempo_entre_llegadas = tiempo_entre_llegadas
        self.ultimos_aleatorios_evento["rnd_llegada"] = rnd
        self.ultimos_aleatorios_evento["t_entre_llegadas"] = tiempo_entre_llegadas
        self._agregar_evento(self.reloj + tiempo_entre_llegadas, 1, self.LLEGADA)

        if len(self.cola) > self.configuracion.maximo_cola_antes_rechazo:
            self.estadisticas.rechazadas += 1
            return

        puesto_libre = self._buscar_puesto_libre()
        if puesto_libre is None:
            self.cola.append(persona)
        else:
            self._iniciar_vacunacion(puesto_libre, persona)

    def _manejar_fin_vacunacion(self, puesto: PuestoVacunacion) -> None:
        if puesto.estado != EstadoPuesto.OCUPADO:
            return

        self.persona_evento_actual = puesto.persona_actual
        self.estado_evento_actual = "Vacunacion"
        if len(self.observacion) >= self.configuracion.capacidad_observacion:
            puesto.bloquear(self.reloj)
            return

        persona = puesto.finalizar_sin_bloqueo()
        if persona is not None:
            self._enviar_a_observacion(persona)
        self._intentar_iniciar_siguiente(puesto)

    def _manejar_fin_observacion(self, persona: Persona) -> None:
        self.observacion.pop(persona.id_persona, None)
        self.persona_evento_actual = persona
        self.estado_evento_actual = "Fin"
        self.estadisticas.completadas += 1
        self.estadisticas.permanencia_acumulada += self.reloj - persona.tiempo_llegada
        self._intentar_desbloquear_puestos()

    def _intentar_desbloquear_puestos(self) -> None:
        for puesto in self.puestos:
            if puesto.estado != EstadoPuesto.BLOQUEADO:
                continue
            if len(self.observacion) >= self.configuracion.capacidad_observacion:
                return
            persona = puesto.liberar_de_bloqueo(self.reloj)
            if persona is not None:
                self._enviar_a_observacion(persona)
            self._intentar_iniciar_siguiente(puesto)

    def _intentar_iniciar_siguiente(self, puesto: PuestoVacunacion) -> None:
        if puesto.esta_libre() and self.cola:
            siguiente_persona = self.cola.popleft()
            self._iniciar_vacunacion(puesto, siguiente_persona)

    def _iniciar_vacunacion(self, puesto: PuestoVacunacion, persona: Persona) -> None:
        rnd, duracion = self.variable_vacunacion.muestrear()
        puesto.iniciar_vacunacion(persona, self.reloj, rnd, duracion)
        self.vacunaciones_por_puesto[puesto.nombre] += 1
        clave_rnd = "rnd_vac_p1" if puesto.nombre == "P1" else "rnd_vac_p2"
        clave_tiempo = "t_vac_p1" if puesto.nombre == "P1" else "t_vac_p2"
        self.ultimos_aleatorios_evento[clave_rnd] = rnd
        self.ultimos_aleatorios_evento[clave_tiempo] = duracion
        self._agregar_evento(puesto.proximo_fin_tiempo, 2, self.FIN_VACUNACION, puesto)

    def _enviar_a_observacion(self, persona: Persona) -> None:
        persona.inicio_observacion = self.reloj
        persona.fin_observacion = self.reloj + self.configuracion.tiempo_observacion
        self.observacion[persona.id_persona] = (persona.fin_observacion, persona)
        self._agregar_evento(persona.fin_observacion, 3, self.FIN_OBSERVACION, persona)

    def _cerrar_bloqueos_abiertos(self) -> None:
        for puesto in self.puestos:
            if puesto.estado == EstadoPuesto.BLOQUEADO and puesto.tiempo_inicio_bloqueo is not None:
                puesto.tiempo_bloqueo_acumulado += self.reloj - puesto.tiempo_inicio_bloqueo
                puesto.tiempo_inicio_bloqueo = self.reloj

    def _buscar_puesto_libre(self) -> Optional[PuestoVacunacion]:
        for puesto in self.puestos:
            if puesto.esta_libre():
                return puesto
        return None

    def _agregar_evento(self, tiempo: float, prioridad: int, tipo_evento: str, carga_util: object = None) -> None:
        heapq.heappush(self.eventos, EventoProgramado(tiempo, prioridad, tipo_evento, carga_util))

    def _tomar_snapshot(self, nombre_evento: str, forzar_final: bool = False) -> None:
        fila = self._construir_fila_estado(nombre_evento)
        self.fila_anterior = self.fila_actual
        self.fila_actual = fila

        debe_guardarse = (
            forzar_final
            or (
                self.reloj >= self.configuracion.mostrar_desde_tiempo
                and len(self.filas_visibles) < self.configuracion.filas_a_mostrar
            )
        )
        if debe_guardarse:
            self.filas_visibles.append(fila)
        if forzar_final:
            self.fila_final = fila
        self.persona_evento_actual = None
        self.estado_evento_actual = None

    def _construir_fila_estado(self, nombre_evento: str) -> Dict[str, Any]:
        proxima_llegada = self._proximo_tiempo_evento(self.LLEGADA)
        proximo_fin_observacion = self._proximo_tiempo_evento(self.FIN_OBSERVACION)
        puesto_1, puesto_2 = self.puestos
        fila = {
            "iteracion": self.iteracion,
            "reloj_min": round(self.reloj, 4),
            "evento": nombre_evento,
            "rnd_llegada": self._formatear(self.ultimos_aleatorios_evento["rnd_llegada"]),
            "t_entre_llegadas": self._formatear(self.ultimos_aleatorios_evento["t_entre_llegadas"]),
            "prox_llegada": self._formatear(proxima_llegada),
            "rnd_vac_p1": self._formatear(self.ultimos_aleatorios_evento["rnd_vac_p1"]),
            "t_vac_p1": self._formatear(self.ultimos_aleatorios_evento["t_vac_p1"]),
            "fin_vac_p1": self._formatear(puesto_1.proximo_fin_tiempo),
            "estado_p1": puesto_1.estado.value,
            "acum_bloq_p1": round(puesto_1.tiempo_bloqueo_acumulado, 4),
            "rnd_vac_p2": self._formatear(self.ultimos_aleatorios_evento["rnd_vac_p2"]),
            "t_vac_p2": self._formatear(self.ultimos_aleatorios_evento["t_vac_p2"]),
            "fin_vac_p2": self._formatear(puesto_2.proximo_fin_tiempo),
            "estado_p2": puesto_2.estado.value,
            "acum_bloq_p2": round(puesto_2.tiempo_bloqueo_acumulado, 4),
            "prox_fin_obs": self._formatear(proximo_fin_observacion),
            "cola_externa": len(self.cola),
            "obs_personas": len(self.observacion),
            "cnt_llegadas": self.estadisticas.llegadas,
            "cnt_rechazadas": self.estadisticas.rechazadas,
            "cnt_completadas": self.estadisticas.completadas,
            "acum_permanencia": round(self.estadisticas.permanencia_acumulada, 4),
            "porc_rechazo": round(self.estadisticas.porcentaje_rechazo, 4),
            "prom_permanencia": round(self.estadisticas.permanencia_promedio, 4),
        }
        self._agregar_columnas_objetos(fila)
        return fila

    def _agregar_columnas_objetos(self, fila: Dict[str, Any]) -> None:
        objetos = self._obtener_objetos_activos()
        self.max_objetos_visibles = max(self.max_objetos_visibles, len(objetos))
        for indice, persona in enumerate(objetos, start=1):
            prefijo = f"obj_{indice:02d}"
            fila[f"{prefijo}_id"] = f"{persona.id_persona} {self._estado_persona(persona)}"
            fila[f"{prefijo}_inicio_vac"] = self._formatear(persona.inicio_vacunacion)
            fila[f"{prefijo}_inicio_obs"] = self._formatear(persona.inicio_observacion)
            fila[f"{prefijo}_fin_atencion"] = self._formatear(persona.fin_observacion)
            fila[f"{prefijo}_total"] = self._total_persona(persona)

    def _obtener_objetos_activos(self) -> List[Persona]:
        objetos: List[Persona] = []
        ids_agregados: set[int] = set()

        for puesto in self.puestos:
            if puesto.persona_actual is None or puesto.persona_actual.id_persona in ids_agregados:
                continue
            objetos.append(puesto.persona_actual)
            ids_agregados.add(puesto.persona_actual.id_persona)

        for persona in self.cola:
            if persona.id_persona in ids_agregados:
                continue
            objetos.append(persona)
            ids_agregados.add(persona.id_persona)

        for _, persona in sorted(self.observacion.values(), key=lambda item: item[0]):
            if persona.id_persona in ids_agregados:
                continue
            objetos.append(persona)
            ids_agregados.add(persona.id_persona)

        if self.persona_evento_actual is not None and self.persona_evento_actual.id_persona not in ids_agregados:
            objetos.append(self.persona_evento_actual)
            ids_agregados.add(self.persona_evento_actual.id_persona)

        return objetos

    def _normalizar_columnas_objetos(self) -> None:
        if self.max_objetos_visibles == 0:
            return
        for fila in self.filas_visibles:
            for indice in range(1, self.max_objetos_visibles + 1):
                prefijo = f"obj_{indice:02d}"
                fila.setdefault(f"{prefijo}_id", None)
                fila.setdefault(f"{prefijo}_inicio_vac", None)
                fila.setdefault(f"{prefijo}_inicio_obs", None)
                fila.setdefault(f"{prefijo}_fin_atencion", None)
                fila.setdefault(f"{prefijo}_total", None)

    def _estado_persona(self, persona: Persona) -> str:
        if self.persona_evento_actual is not None and persona.id_persona == self.persona_evento_actual.id_persona and self.estado_evento_actual == "Fin":
            return "Fin"
        if any(
            puesto.persona_actual is not None and puesto.persona_actual.id_persona == persona.id_persona
            for puesto in self.puestos
        ):
            return "Vacunacion"
        if persona.id_persona in self.observacion:
            return "Observacion"
        if any(persona_cola.id_persona == persona.id_persona for persona_cola in self.cola):
            return "Cola"
        return self.estado_evento_actual or "Sistema"

    def _total_persona(self, persona: Persona) -> Optional[float]:
        if persona.fin_observacion is None:
            return None
        return round(persona.fin_observacion - persona.tiempo_llegada, 4)

    def _proximo_tiempo_evento(self, tipo_evento: str) -> Optional[float]:
        tiempos = [evento.time for evento in self.eventos if evento.tipo_evento == tipo_evento]
        return min(tiempos) if tiempos else None

    @staticmethod
    def _formatear(valor: Optional[float]) -> Optional[float]:
        if valor is None:
            return None
        return round(valor, 4)

    def _reiniciar_ultimos_aleatorios_evento(self) -> None:
        for clave in self.ultimos_aleatorios_evento:
            self.ultimos_aleatorios_evento[clave] = None

    def _destruir_objetos_de_ejecucion(self) -> None:
        self.cola.clear()
        self.observacion.clear()
        self.eventos.clear()
        self.fila_anterior = None
        self.fila_actual = None
