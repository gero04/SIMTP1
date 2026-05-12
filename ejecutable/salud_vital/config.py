# En este archivo configuramos los parametros para la simulacion

from dataclasses import dataclass

@dataclass
class ConfiguracionSimulacion:

    # NOTA: Todos los tiempos estan expresados en minutos

    # ---> Parametros de control de la simulacion
    # --> El tiempo maximo a simular
    tiempo_simulacion: float

    # --> La cantidad maxima de iteraciones para que no nos metamos en un loop infinito
    maximo_iteraciones: int = 100000

    # ---> Parametros de visualizacion del vector de estado
    # --> A partir de que minuto guardamos filas (0 es desde el inicio)
    mostrar_desde_tiempo: float = 0.0
    # --> La cantidad de filas que mostramos en el vector de retorno
    filas_a_mostrar: int = 100

    # ---> Distribucion exponencial negativa (corresponde a las llegadas)
    # --> Media entre las llegadas medida en minutos
    media_llegada: float = 6.0

    # ---> Distribucion de vacunación (Uniforme)
    # --> Tiempo minimo de vacunacion (en minutos)
    vacunacion_minima: float = 3.0
    # --> Tiempo maximo de vacunacion (en minutos)
    vacunacion_maxima: float = 7.0

    # ---> Parametros de observacion post vacunacion
    # --> Tiempo maximo de observacion (minutos)
    tiempo_observacion: float = 15.0
    # --> Capacidad maxima de la zona de observacion (en personas)
    capacidad_observacion: int = 20

    # ---> Si la cola se pasa de este valor se empiezan a rechazar las personas nuevas
    maximo_cola_antes_rechazo: int = 10

    # ---> Por si queremos reproducir el problema esta variable sirve para ello
    seed: int | None = None
