import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .config import ConfiguracionSimulacion
from .exporter import ExportadorVectorEstado
from .simulator import SimuladorCentroVacunacion


class AplicacionSimulacion(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Simulador Centro de Vacunacion Salud Vital")
        self.geometry("1280x780")
        self.filas: List[Dict[str, Any]] = []
        self.resumen: Dict[str, float] = {}
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

        self.tabla = ttk.Treeview(marco_tabla, show="headings")
        scroll_vertical = ttk.Scrollbar(marco_tabla, orient="vertical", command=self.tabla.yview)
        scroll_horizontal = ttk.Scrollbar(marco_tabla, orient="horizontal", command=self.tabla.xview)
        self.tabla.configure(yscrollcommand=scroll_vertical.set, xscrollcommand=scroll_horizontal.set)
        self.tabla.grid(row=0, column=0, sticky="nsew")
        scroll_vertical.grid(row=0, column=1, sticky="ns")
        scroll_horizontal.grid(row=1, column=0, sticky="ew")
        marco_tabla.rowconfigure(0, weight=1)
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
        if not self.filas:
            return
        columnas = list(self.filas[0].keys())
        self.tabla["columns"] = columnas
        for columna in columnas:
            self.tabla.heading(columna, text=columna)
            self.tabla.column(columna, width=115, anchor="center")
        for fila in self.filas:
            self.tabla.insert("", "end", values=[fila.get(columna, "") for columna in columnas])

    def _completar_resumen(self) -> None:
        self.texto_resumen.delete("1.0", "end")
        lineas = [
            "Resultados de la simulacion",
            f"Personas llegadas: {self.resumen.get('personas_llegadas', 0):.0f}",
            f"Personas rechazadas: {self.resumen.get('personas_rechazadas', 0):.0f}",
            f"Personas completadas: {self.resumen.get('personas_completadas', 0):.0f}",
            f"Porcentaje rechazo: {self.resumen.get('porcentaje_rechazo', 0):.4f}%",
            f"Bloqueo promedio puestos: {self.resumen.get('bloqueo_promedio_puestos', 0):.4f} min",
            f"Bloqueo P1: {self.resumen.get('bloqueo_p1', 0):.4f} min",
            f"Bloqueo P2: {self.resumen.get('bloqueo_p2', 0):.4f} min",
            f"Permanencia promedio: {self.resumen.get('permanencia_promedio', 0):.4f} min",
        ]
        self.texto_resumen.insert("end", "\n".join(lineas))

    def _dibujar_grafico(self) -> None:
        self.grafico.clear()
        etiquetas = ["Llegadas", "Rechazadas", "Completadas"]
        valores = [
            self.resumen.get("personas_llegadas", 0),
            self.resumen.get("personas_rechazadas", 0),
            self.resumen.get("personas_completadas", 0),
        ]
        self.grafico.bar(etiquetas, valores)
        self.grafico.set_title("Resumen")
        self.grafico.set_ylabel("Personas")
        self.figure.tight_layout()
        self.canvas.draw()

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
