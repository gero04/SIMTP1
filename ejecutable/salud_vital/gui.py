import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .config import ConfiguracionSimulacion
from .exporter import ExportadorVectorEstado
from .simulator import SimuladorCentroVacunacion


class AplicacionSimulacion(tk.Tk):
    COLOR_ITERACION = "#F000FF"
    COLOR_EVENTO = "#E7D1D8"
    COLOR_RELOJ = "#E7D1D8"
    COLOR_LLEGADA = "#9FC5E8"
    COLOR_COLA = "#CFE2F3"
    COLOR_P1 = "#2E86AB"
    COLOR_P2 = "#F18F01"
    COLOR_OBSERVACION = "#8E7CC3"
    COLOR_ESTADISTICAS = "#D9EAD3"
    COLOR_OBJETOS = "#EFEFEF"

    def __init__(self) -> None:
        super().__init__()
        self.title("Simulador Centro de Vacunacion Salud Vital")
        self.geometry("1280x780")
        self.filas: List[Dict[str, Any]] = []
        self.resumen: Dict[str, float] = {}
        self.ancho_total_tabla = 0
        self._construir_diseno()

    def _construir_diseno(self) -> None:
        formulario = ttk.LabelFrame(self, text="Parametros")
        formulario.pack(fill="x", padx=10, pady=8)

        self.entradas: dict[str, tk.StringVar] = {}
        campos = [
            ("tiempo_simulacion", "Tiempo X (min)", "480"),
            ("maximo_iteraciones", "Max. iteraciones", "100000"),
            ("mostrar_desde_tiempo", "Mostrar desde hora j", "0"),
            ("filas_a_mostrar", "Filas i", "100"),
            ("media_llegada", "Media llegada", "6"),
            ("vacunacion_minima", "Vac. min.", "3"),
            ("vacunacion_maxima", "Vac. max.", "7"),
            ("tiempo_observacion", "Obs. fija", "15"),
            ("capacidad_observacion", "Cap. obs.", "20"),
            ("maximo_cola_antes_rechazo", "Max. cola antes rechazo", "10"),
            ("seed", "Seed opcional", ""),
        ]

        for indice, (clave, etiqueta, valor_por_defecto) in enumerate(campos):
            ttk.Label(formulario, text=etiqueta).grid(row=indice // 4, column=(indice % 4) * 2, sticky="w", padx=5, pady=4)
            variable = tk.StringVar(value=valor_por_defecto)
            self.entradas[clave] = variable
            ttk.Entry(formulario, textvariable=variable, width=16).grid(row=indice // 4, column=(indice % 4) * 2 + 1, padx=5, pady=4)

        ttk.Button(formulario, text="Ejecutar", command=self.ejecutar_simulacion).grid(row=3, column=0, padx=5, pady=6, sticky="ew")
        ttk.Button(formulario, text="Exportar CSV", command=self.exportar_csv).grid(row=3, column=1, padx=5, pady=6, sticky="ew")
        ttk.Button(formulario, text="Exportar XLSX", command=self.exportar_xlsx).grid(row=3, column=2, padx=5, pady=6, sticky="ew")

        panel_principal = ttk.PanedWindow(self, orient="vertical")
        panel_principal.pack(fill="both", expand=True, padx=10, pady=8)

        marco_tabla = ttk.Frame(panel_principal)
        panel_principal.add(marco_tabla, weight=4)

        self.cabecera_canvas = tk.Canvas(marco_tabla, height=44, highlightthickness=0, bg="white")
        self.cabecera_canvas.grid(row=0, column=0, sticky="ew")

        self.tabla = ttk.Treeview(marco_tabla, show="headings")
        scroll_vertical = ttk.Scrollbar(marco_tabla, orient="vertical", command=self.tabla.yview)
        self.scroll_horizontal = ttk.Scrollbar(marco_tabla, orient="horizontal", command=self._desplazar_horizontal)
        self.tabla.configure(yscrollcommand=scroll_vertical.set, xscrollcommand=self._sincronizar_scroll_x)
        self.tabla.grid(row=1, column=0, sticky="nsew")
        scroll_vertical.grid(row=1, column=1, sticky="ns")
        self.scroll_horizontal.grid(row=2, column=0, sticky="ew")
        marco_tabla.rowconfigure(1, weight=1)
        marco_tabla.columnconfigure(0, weight=1)

        marco_inferior = ttk.Frame(panel_principal)
        panel_principal.add(marco_inferior, weight=2)
        self.texto_resumen = tk.Text(marco_inferior, height=8, width=60)
        self.texto_resumen.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.figure = Figure(figsize=(5, 2.5), dpi=100)
        self.grafico = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=marco_inferior)
        self.canvas.get_tk_widget().pack(side="right", fill="both", expand=True)

    def ejecutar_simulacion(self) -> None:
        try:
            configuracion = self._leer_configuracion()
            simulador = SimuladorCentroVacunacion(configuracion)
            self.filas = simulador.ejecutar()
            self.resumen = simulador.obtener_resumen()
            self._completar_tabla()
            self._completar_resumen()
            self._dibujar_grafico()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _leer_configuracion(self) -> ConfiguracionSimulacion:
        seed_texto = self.entradas["seed"].get().strip()
        return ConfiguracionSimulacion(
            tiempo_simulacion=float(self.entradas["tiempo_simulacion"].get()),
            maximo_iteraciones=int(self.entradas["maximo_iteraciones"].get()),
            mostrar_desde_tiempo=float(self.entradas["mostrar_desde_tiempo"].get()),
            filas_a_mostrar=int(self.entradas["filas_a_mostrar"].get()),
            media_llegada=float(self.entradas["media_llegada"].get()),
            vacunacion_minima=float(self.entradas["vacunacion_minima"].get()),
            vacunacion_maxima=float(self.entradas["vacunacion_maxima"].get()),
            tiempo_observacion=float(self.entradas["tiempo_observacion"].get()),
            capacidad_observacion=int(self.entradas["capacidad_observacion"].get()),
            maximo_cola_antes_rechazo=int(self.entradas["maximo_cola_antes_rechazo"].get()),
            seed=int(seed_texto) if seed_texto else None,
        )

    def _completar_tabla(self) -> None:
        self.tabla.delete(*self.tabla.get_children())
        self.cabecera_canvas.delete("all")
        if not self.filas:
            return
        columnas = self._ordenar_columnas(list(self.filas[0].keys()))
        self.tabla["columns"] = columnas
        self.ancho_total_tabla = 0
        for columna in columnas:
            ancho = self._ancho_columna(columna)
            self.tabla.heading(columna, text=self._titulo_columna(columna))
            self.tabla.column(columna, width=ancho, minwidth=ancho, stretch=False, anchor="center")
            self.ancho_total_tabla += ancho
        for fila in self.filas:
            self.tabla.insert("", "end", values=[fila.get(columna, "") for columna in columnas])
        self._dibujar_cabecera_grupos(columnas)

    def _completar_resumen(self) -> None:
        self.texto_resumen.delete("1.0", "end")
        lineas = [
            "Resultados de la simulacion",
            f"Personas llegadas: {self.resumen.get('personas_llegadas', 0):.0f}",
            f"Personas rechazadas: {self.resumen.get('personas_rechazadas', 0):.0f}",
            f"Personas completadas: {self.resumen.get('personas_completadas', 0):.0f}",
            f"Porcentaje rechazo: {self.resumen.get('porcentaje_rechazo', 0):.4f}%",
            f"Bloqueo promedio puestos: {self.resumen.get('bloqueo_promedio_puestos', 0):.4f} min",
            f"Vacunacion 1 atendidas: {self.resumen.get('vacunaciones_p1', 0):.0f}",
            f"Vacunacion 2 atendidas: {self.resumen.get('vacunaciones_p2', 0):.0f}",
            f"Bloqueo P1: {self.resumen.get('bloqueo_p1', 0):.4f} min",
            f"Bloqueo P2: {self.resumen.get('bloqueo_p2', 0):.4f} min",
            f"Permanencia promedio: {self.resumen.get('permanencia_promedio', 0):.4f} min",
        ]
        self.texto_resumen.insert("end", "\n".join(lineas))

    def _dibujar_grafico(self) -> None:
        self.grafico.clear()
        etiquetas = ["Atenciones", "Bloqueo (min)"]
        valores_p1 = [
            self.resumen.get("vacunaciones_p1", 0),
            self.resumen.get("bloqueo_p1", 0),
        ]
        valores_p2 = [
            self.resumen.get("vacunaciones_p2", 0),
            self.resumen.get("bloqueo_p2", 0),
        ]
        posiciones = list(range(len(etiquetas)))
        ancho = 0.35

        posiciones_p1 = [posicion - ancho / 2 for posicion in posiciones]
        posiciones_p2 = [posicion + ancho / 2 for posicion in posiciones]
        self.grafico.bar(posiciones_p1, valores_p1, width=ancho, color=self.COLOR_P1, label="Vacunacion 1")
        self.grafico.bar(posiciones_p2, valores_p2, width=ancho, color=self.COLOR_P2, label="Vacunacion 2")
        self.grafico.set_xticks(posiciones, etiquetas)
        self.grafico.set_title("Comparacion por puesto")
        self.grafico.legend()
        self.grafico.grid(axis="y", alpha=0.25)
        self.figure.tight_layout()
        self.canvas.draw()

    def _dibujar_cabecera_grupos(self, columnas: List[str]) -> None:
        self.cabecera_canvas.delete("all")
        if not columnas:
            return

        grupos = self._definir_grupos(columnas)
        posiciones = self._posiciones_columnas(columnas)
        altura_total = 44
        altura_superior = 20
        altura_inferior = altura_total - altura_superior

        for grupo in grupos:
            inicio = posiciones[grupo["desde"]]
            fin = posiciones[grupo["hasta"] + 1]
            subgrupos = grupo.get("subgrupos", [])
            if subgrupos:
                self.cabecera_canvas.create_rectangle(
                    inicio,
                    0,
                    fin,
                    altura_superior,
                    fill=grupo["color"],
                    outline="#B7B7B7",
                )
                self.cabecera_canvas.create_text(
                    (inicio + fin) / 2,
                    altura_superior / 2,
                    text=grupo["titulo"],
                    font=("Segoe UI", 10, "bold"),
                )
                for subgrupo in subgrupos:
                    sub_inicio = posiciones[subgrupo["desde"]]
                    sub_fin = posiciones[subgrupo["hasta"] + 1]
                    self.cabecera_canvas.create_rectangle(
                        sub_inicio,
                        altura_superior,
                        sub_fin,
                        altura_total,
                        fill=subgrupo["color"],
                        outline="#B7B7B7",
                    )
                    self.cabecera_canvas.create_text(
                        (sub_inicio + sub_fin) / 2,
                        altura_superior + (altura_inferior / 2),
                        text=subgrupo["titulo"],
                        font=("Segoe UI", 9),
                    )
                continue

            self.cabecera_canvas.create_rectangle(
                inicio,
                0,
                fin,
                altura_total,
                fill=grupo["color"],
                outline="#B7B7B7",
            )
            self.cabecera_canvas.create_text(
                (inicio + fin) / 2,
                altura_total / 2,
                text=grupo["titulo"],
                font=("Segoe UI", 10, "bold"),
            )

        self.cabecera_canvas.configure(scrollregion=(0, 0, self.ancho_total_tabla, altura_total))
        self.cabecera_canvas.xview_moveto(self.tabla.xview()[0] if self.tabla.xview() else 0)

    def _definir_grupos(self, columnas: List[str]) -> List[Dict[str, Any]]:
        grupos: List[Dict[str, Any]] = []

        for clave_inicio, titulo, color in [
            ("iteracion", "Cantidad", self.COLOR_ITERACION),
            ("evento", "Evento", self.COLOR_EVENTO),
            ("reloj_min", "Reloj", self.COLOR_RELOJ),
            ("rnd_llegada", "LLEGADA PACIENTE", self.COLOR_LLEGADA),
            ("cola_externa", "Cola de espera", self.COLOR_COLA),
            ("prox_fin_obs", "Observacion", self.COLOR_OBSERVACION),
            ("cnt_llegadas", "Estadisticas", self.COLOR_ESTADISTICAS),
        ]:
            indices = self._buscar_rango_grupo(columnas, clave_inicio)
            if indices is not None:
                grupos.append({"desde": indices[0], "hasta": indices[1], "titulo": titulo, "color": color})

        rango_p1 = self._buscar_rango_grupo(columnas, "rnd_vac_p1")
        rango_p2 = self._buscar_rango_grupo(columnas, "rnd_vac_p2")
        if rango_p1 is not None and rango_p2 is not None:
            grupos.append(
                {
                    "desde": rango_p1[0],
                    "hasta": rango_p2[1],
                    "titulo": "Vacunacion",
                    "color": self.COLOR_P2,
                    "subgrupos": [
                        {"desde": rango_p1[0], "hasta": rango_p1[1], "titulo": "Puesto 1", "color": "#F9CB9C"},
                        {"desde": rango_p2[0], "hasta": rango_p2[1], "titulo": "Puesto 2", "color": "#F6B26B"},
                    ],
                }
            )

        subgrupos_objetos: List[Dict[str, Any]] = []
        inicio_objetos: Optional[int] = None
        fin_objetos: Optional[int] = None
        for indice, columna in enumerate(columnas):
            if not columna.startswith("obj_") or not columna.endswith("_id"):
                continue
            numero_objeto = int(columna.split("_")[1])
            desde = indice
            hasta = min(indice + 4, len(columnas) - 1)
            if inicio_objetos is None:
                inicio_objetos = desde
            fin_objetos = hasta
            subgrupos_objetos.append({"desde": desde, "hasta": hasta, "titulo": str(numero_objeto), "color": self.COLOR_OBJETOS})

        if inicio_objetos is not None and fin_objetos is not None:
            grupos.append(
                {
                    "desde": inicio_objetos,
                    "hasta": fin_objetos,
                    "titulo": "Seguimiento pacientes",
                    "color": "#D04423",
                    "subgrupos": subgrupos_objetos,
                }
            )

        return sorted(grupos, key=lambda grupo: grupo["desde"])

    @staticmethod
    def _buscar_rango_grupo(columnas: List[str], clave_inicio: str) -> tuple[int, int] | None:
        if clave_inicio not in columnas:
            return None

        desde = columnas.index(clave_inicio)
        if clave_inicio == "rnd_llegada":
            return desde, columnas.index("prox_llegada")
        if clave_inicio == "cola_externa":
            return desde, desde
        if clave_inicio == "rnd_vac_p1":
            return desde, columnas.index("acum_bloq_p1")
        if clave_inicio == "rnd_vac_p2":
            return desde, columnas.index("acum_bloq_p2")
        if clave_inicio == "prox_fin_obs":
            return desde, columnas.index("obs_personas")
        if clave_inicio == "cnt_llegadas":
            return desde, columnas.index("prom_permanencia")
        return desde, desde

    @staticmethod
    def _ordenar_columnas(columnas: List[str]) -> List[str]:
        columnas_objetos = sorted(
            [columna for columna in columnas if columna.startswith("obj_")],
            key=lambda columna: (int(columna.split("_")[1]), AplicacionSimulacion._orden_objeto(columna)),
        )
        columnas_base = [
            "iteracion",
            "evento",
            "reloj_min",
            "rnd_llegada",
            "t_entre_llegadas",
            "prox_llegada",
            "cola_externa",
            "rnd_vac_p1",
            "t_vac_p1",
            "fin_vac_p1",
            "estado_p1",
            "acum_bloq_p1",
            "rnd_vac_p2",
            "t_vac_p2",
            "fin_vac_p2",
            "estado_p2",
            "acum_bloq_p2",
            "prox_fin_obs",
            "obs_personas",
            "cnt_llegadas",
            "cnt_rechazadas",
            "cnt_completadas",
            "acum_permanencia",
            "porc_rechazo",
            "prom_permanencia",
        ]
        columnas_presentes = [columna for columna in columnas_base if columna in columnas]
        return columnas_presentes + columnas_objetos

    @staticmethod
    def _orden_objeto(columna: str) -> int:
        if columna.endswith("_id"):
            return 0
        if columna.endswith("_inicio_vac"):
            return 1
        if columna.endswith("_inicio_obs"):
            return 2
        if columna.endswith("_fin_atencion"):
            return 3
        if columna.endswith("_total"):
            return 4
        if columna.endswith("_puesto"):
            return 5
        return 99

    def _posiciones_columnas(self, columnas: List[str]) -> List[int]:
        posiciones = [0]
        acumulado = 0
        for columna in columnas:
            acumulado += self._ancho_columna(columna)
            posiciones.append(acumulado)
        return posiciones

    def _desplazar_horizontal(self, *args: Any) -> None:
        self.tabla.xview(*args)
        self.cabecera_canvas.xview(*args)

    def _sincronizar_scroll_x(self, primero: str, ultimo: str) -> None:
        self.scroll_horizontal.set(primero, ultimo)
        self.cabecera_canvas.xview_moveto(float(primero))

    @staticmethod
    def _titulo_columna(columna: str) -> str:
        if columna.startswith("obj_"):
            indice = int(columna.split("_")[1])
            if columna.endswith("_id"):
                return "ID"
            if columna.endswith("_inicio_vac"):
                return "Inicio vacunacion"
            if columna.endswith("_inicio_obs"):
                return "Inicio observacion"
            if columna.endswith("_fin_atencion"):
                return "Final"
            if columna.endswith("_total"):
                return "Total"
            if columna.endswith("_puesto"):
                return "Puesto"
        titulos = {
            "iteracion": "Cantidad",
            "reloj_min": "Reloj",
            "evento": "Evento",
            "rnd_llegada": "RND llegada",
            "t_entre_llegadas": "Tiempo llegada",
            "prox_llegada": "Proxima llegada",
            "rnd_vac_p1": "RND",
            "t_vac_p1": "Tiempo atencion",
            "fin_vac_p1": "Tiempo Fin aten",
            "estado_p1": "Estado",
            "acum_bloq_p1": "Bloq. acum.",
            "rnd_vac_p2": "RND",
            "t_vac_p2": "Tiempo atencion",
            "fin_vac_p2": "Tiempo Fin aten",
            "estado_p2": "Estado",
            "acum_bloq_p2": "Bloq. acum.",
            "prox_fin_obs": "Prox. fin obs.",
            "cola_externa": "Cola de espera",
            "obs_personas": "Cant. pacientes",
            "cnt_llegadas": "Llegadas",
            "cnt_rechazadas": "Rechazadas",
            "cnt_completadas": "Completadas",
            "acum_permanencia": "Ac. permanencia",
            "porc_rechazo": "% rechazo",
            "prom_permanencia": "Prom. permanencia",
        }
        return titulos.get(columna, columna)

    @staticmethod
    def _ancho_columna(columna: str) -> int:
        if columna.startswith("obj_"):
            if columna.endswith("_id"):
                return 100
            if columna.endswith("_total"):
                return 90
            if columna.endswith("_puesto"):
                return 80
            return 120
        if columna == "evento":
            return 130
        if columna in {"t_entre_llegadas", "prox_llegada", "t_vac_p1", "t_vac_p2", "fin_vac_p1", "fin_vac_p2"}:
            return 120
        if columna in {"iteracion", "rnd_llegada", "rnd_vac_p1", "rnd_vac_p2", "cola_externa", "obs_personas"}:
            return 90
        return 95

    def exportar_csv(self) -> None:
        if not self.filas:
            messagebox.showinfo("Sin datos", "Primero ejecuta la simulacion.")
            return
        ruta = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if ruta:
            ExportadorVectorEstado(self.filas).exportar_csv(ruta)

    def exportar_xlsx(self) -> None:
        if not self.filas:
            messagebox.showinfo("Sin datos", "Primero ejecuta la simulacion.")
            return
        ruta = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if ruta:
            ExportadorVectorEstado(self.filas).exportar_xlsx(ruta)
