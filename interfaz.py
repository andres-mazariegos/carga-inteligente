# =====================================================================
#   CARGA INTELIGENTE · INTERFAZ GRÁFICA (Tkinter)
#   Solo se encarga de PEDIR los datos y MOSTRAR los resultados.
#   La búsqueda está en busqueda.py (separada de la visualización).
#
#   Entradas: escenario base, inicio, meta, litros, rendimiento, tanque,
#             precios de cada gasolinera, km y tramos cerrados.
#   Salidas:  mapa con la ruta, ejecución paso a paso, plan,
#             comparación de algoritmos, iteraciones de A* y Google Maps.
#
#   Ejecutar:  python interfaz.py      (Tkinter ya viene con Python)
# =====================================================================

import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox

from busqueda import (ESCENARIOS, NOMBRES, PRECIOS_BASE, TRAMOS, Escenario,
                      lugares_del_plan, resolver)
from carga_inteligente import enlace_google_maps

# Posición (x, y) de cada nodo en el dibujo del mapa
POSICIONES = {"CHAP": (60, 175), "T1": (150, 85), "T2": (250, 65), "T3": (350, 85),
              "T4": (460, 100), "J1": (310, 190), "J2": (470, 205), "K1": (150, 290),
              "K2": (285, 315), "K3": (420, 305), "SUCH": (590, 175), "UP": (695, 175)}
NEGRO, GRIS, GRIS_CLARO = "#1A1A1A", "#9A9A9A", "#F2F2F2"
OPCIONES_LUGAR = [f"{k} · {v}" for k, v in NOMBRES.items()]   # para los combos de inicio/meta


class Aplicacion(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Carga Inteligente · Búsqueda A*")
        self.geometry("1280x800")
        self.minsize(1150, 760)
        self.configure(background="white")
        self.trayectoria = []        # nodos del plan (para ejecutarlo paso a paso)
        self.paso = 0                # paso que se está mostrando
        self.escenario = None        # último escenario leído
        self.ultimo = None           # último resultado de A*
        self._estilos()
        self._crear_entradas()
        self._crear_salidas()
        self.cargar_escenario()
        self.dibujar_mapa()

    # ================================================================
    # ESTILO: blanco, negro y grises
    # ================================================================
    def _estilos(self):
        e = ttk.Style(self)
        e.theme_use("clam")
        e.configure(".", font=("Arial", 10), background="white")
        e.configure("TLabelframe.Label", font=("Arial", 10, "bold"))
        e.configure("Titulo.TLabel", font=("Arial", 15, "bold"))
        e.configure("Treeview.Heading", font=("Arial", 10, "bold"), background="#D9D9D9")
        e.configure("Accion.TButton", font=("Arial", 11, "bold"), padding=5)

    # ================================================================
    # PANEL IZQUIERDO: DATOS DE ENTRADA
    # ================================================================
    def _crear_entradas(self):
        izq = ttk.Frame(self, padding=(10, 6))
        izq.pack(side="left", fill="y")
        ttk.Label(izq, text="Datos de entrada", style="Titulo.TLabel").pack(anchor="w")

        # 1) Escenario base
        caja = ttk.LabelFrame(izq, text="Escenario base", padding=5)
        caja.pack(fill="x", pady=2)
        self.combo = ttk.Combobox(caja, state="readonly", width=34,
                                  values=[e.nombre for e in ESCENARIOS])
        self.combo.current(0)
        self.combo.pack(side="left")
        ttk.Button(caja, text="Cargar", command=self.cargar_escenario).pack(side="left", padx=4)

        # 2) Inicio y meta
        ruta = ttk.LabelFrame(izq, text="Ruta", padding=5)
        ruta.pack(fill="x", pady=2)
        ttk.Label(ruta, text="Inicio:").grid(row=0, column=0, sticky="w")
        self.inicio = ttk.Combobox(ruta, state="readonly", width=40, values=OPCIONES_LUGAR)
        self.inicio.grid(row=0, column=1, pady=1)
        ttk.Label(ruta, text="Meta:").grid(row=1, column=0, sticky="w")
        self.meta = ttk.Combobox(ruta, state="readonly", width=40, values=OPCIONES_LUGAR)
        self.meta.grid(row=1, column=1, pady=1)

        # 3) Vehículo
        auto = ttk.LabelFrame(izq, text="Vehículo", padding=5)
        auto.pack(fill="x", pady=2)
        self.litros = self._campo(auto, "Litros iniciales:", 0, 0)
        self.rendimiento = self._campo(auto, "Rendimiento (km/L):", 0, 2)
        self.capacidad = self._campo(auto, "Tanque (L):", 1, 0)

        # 4) Precios
        gas = ttk.LabelFrame(izq, text="Precio de la Magna por gasolinera ($/L)", padding=5)
        gas.pack(fill="x", pady=2)
        self.precios = {}
        for i, clave in enumerate(PRECIOS_BASE):
            ttk.Label(gas, text=clave, width=5).grid(row=i // 3, column=(i % 3) * 2, sticky="w")
            e = ttk.Entry(gas, width=7)
            e.grid(row=i // 3, column=(i % 3) * 2 + 1, padx=(0, 10), pady=1)
            self.precios[clave] = e

        # 5) Tramos
        tr = ttk.LabelFrame(izq, text="Tramos (km) · marcar = cerrado", padding=5)
        tr.pack(fill="x", pady=2)
        self.km, self.cerrados = {}, {}
        for i, (a, b, _) in enumerate(TRAMOS):
            fila, col = i % 7, (i // 7) * 3
            ttk.Label(tr, text=f"{a}–{b}", width=9).grid(row=fila, column=col, sticky="w")
            e = ttk.Entry(tr, width=6)
            e.grid(row=fila, column=col + 1, pady=1)
            v = tk.BooleanVar()
            ttk.Checkbutton(tr, variable=v).grid(row=fila, column=col + 2, padx=(0, 8))
            self.km[(a, b)], self.cerrados[(a, b)] = e, v

        ttk.Button(izq, text="▶  Buscar plan óptimo", style="Accion.TButton",
                   command=self.buscar_plan).pack(fill="x", pady=(8, 2))
        ttk.Button(izq, text="Abrir ruta en Google Maps", command=self.abrir_maps).pack(fill="x")

    def _campo(self, padre, texto, fila, col):
        """Etiqueta + caja de texto."""
        ttk.Label(padre, text=texto).grid(row=fila, column=col, sticky="w", pady=1)
        e = ttk.Entry(padre, width=7)
        e.grid(row=fila, column=col + 1, sticky="w", padx=(4, 12))
        return e

    # ================================================================
    # PANEL DERECHO: SALIDAS
    # ================================================================
    def _crear_salidas(self):
        der = ttk.Frame(self, padding=(10, 6))
        der.pack(side="left", fill="both", expand=True)
        ttk.Label(der, text="Resultados", style="Titulo.TLabel").pack(anchor="w")

        self.canvas = tk.Canvas(der, width=760, height=355, bg="white",
                                highlightthickness=1, highlightbackground="#BFBFBF")
        self.canvas.pack(fill="x", pady=2)
        self.resumen = ttk.Label(der, text="Escribe los datos y presiona «Buscar plan óptimo».",
                                 font=("Arial", 11, "bold"))
        self.resumen.pack(anchor="w", pady=2)

        # Controles para ejecutar el plan paso a paso
        ej = ttk.LabelFrame(der, text="Ejecución del plan", padding=4)
        ej.pack(fill="x", pady=2)
        botones = ttk.Frame(ej)
        botones.pack(fill="x")
        for texto, cmd in (("|◀ Inicio", lambda: self.ir_a(0)), ("◀ Anterior", lambda: self.ir_a(self.paso - 1)),
                           ("Siguiente ▶", lambda: self.ir_a(self.paso + 1)),
                           ("Final ▶|", lambda: self.ir_a(len(self.trayectoria) - 1)),
                           ("Reproducir", self.reproducir)):
            ttk.Button(botones, text=texto, width=12, command=cmd).pack(side="left", padx=2)
        self.lbl_paso = ttk.Label(ej, text="Paso 0 / 0", font=("Arial", 10, "bold"))
        self.lbl_paso.pack(anchor="w", pady=(4, 0))

        pestanas = ttk.Notebook(der)
        pestanas.pack(fill="both", expand=True, pady=2)
        self.pestanas = pestanas
        self.txt_plan = self._texto(pestanas, "Plan de A*")
        marco = ttk.Frame(pestanas)
        pestanas.add(marco, text="Comparación de algoritmos")
        cols = ("alg", "gasto", "exp", "front", "ms", "opt")
        self.tabla = ttk.Treeview(marco, columns=cols, show="headings", height=5)
        for c, t in zip(cols, ("Algoritmo", "Gasto ($)", "Expandidos", "Frontera máx.",
                               "Tiempo (ms)", "¿Óptimo?")):
            self.tabla.heading(c, text=t)
            self.tabla.column(c, anchor="center", width=110)
        self.tabla.pack(fill="both", expand=True)
        self.txt_iter = self._texto(pestanas, "Iteraciones de A*")

    def _texto(self, pestanas, titulo):
        marco = ttk.Frame(pestanas)
        pestanas.add(marco, text=titulo)
        t = tk.Text(marco, font=("Consolas", 10), height=8, wrap="none", relief="flat")
        barra = ttk.Scrollbar(marco, command=t.yview)
        t.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        t.pack(fill="both", expand=True)
        return t

    # ================================================================
    # LEER DATOS
    # ================================================================
    def cargar_escenario(self):
        """Llena los campos con un escenario predefinido."""
        esc = ESCENARIOS[self.combo.current()]
        self.inicio.current(list(NOMBRES).index(esc.inicio))
        self.meta.current(list(NOMBRES).index(esc.meta))
        self._poner(self.litros, esc.litros_iniciales)
        self._poner(self.rendimiento, esc.rendimiento)
        self._poner(self.capacidad, esc.capacidad)
        for clave, e in self.precios.items():
            self._poner(e, esc.precios_especiales.get(clave, PRECIOS_BASE[clave]))
        cerrados = {frozenset(t) for t in esc.tramos_cerrados}
        for a, b, km in TRAMOS:
            self._poner(self.km[(a, b)], km)
            self.cerrados[(a, b)].set(frozenset((a, b)) in cerrados)
        self.escenario, self.trayectoria = esc, []       # vista previa del escenario cargado
        if hasattr(self, "canvas"):
            self.dibujar_mapa()

    @staticmethod
    def _poner(entrada, valor):
        entrada.delete(0, "end")
        entrada.insert(0, str(valor))

    @staticmethod
    def _leer_numero(entrada, nombre, minimo=0.0):
        """Convierte el texto a número y valida que sea correcto."""
        try:
            valor = float(entrada.get().replace(",", "."))
        except ValueError:
            raise ValueError(f"«{nombre}» debe ser un número.")
        if valor < minimo:
            raise ValueError(f"«{nombre}» no puede ser menor que {minimo}.")
        return valor

    def leer_escenario(self):
        """Arma un Escenario con lo que el usuario escribió."""
        inicio = self.inicio.get().split(" · ")[0]
        meta = self.meta.get().split(" · ")[0]
        if inicio == meta:
            raise ValueError("El inicio y la meta deben ser lugares distintos.")
        litros = self._leer_numero(self.litros, "Litros iniciales")
        rend = self._leer_numero(self.rendimiento, "Rendimiento", 0.1)
        cap = self._leer_numero(self.capacidad, "Tanque", 1)
        if litros > cap:
            raise ValueError("Los litros iniciales no pueden ser más que la capacidad del tanque.")
        precios = {c: self._leer_numero(e, f"Precio {c}", 0.01) for c, e in self.precios.items()}
        km = {t: self._leer_numero(e, f"Tramo {t[0]}–{t[1]}", 0.1) for t, e in self.km.items()}
        cerrados = [t for t, v in self.cerrados.items() if v.get()]
        return Escenario("Datos del usuario", "Ingresados en la interfaz", litros,
                         precios_especiales=precios, tramos_cerrados=cerrados,
                         km_especiales=km, rendimiento=rend, capacidad=cap,
                         inicio=inicio, meta=meta)

    # ================================================================
    # BUSCAR Y MOSTRAR
    # ================================================================
    def buscar_plan(self):
        try:
            self.escenario = self.leer_escenario()
        except ValueError as error:
            messagebox.showerror("Dato incorrecto", str(error))
            return

        iteraciones = []
        problema, resultados = resolver(self.escenario, iteraciones)
        self.txt_plan.delete("1.0", "end")
        self.txt_iter.delete("1.0", "end")
        self.tabla.delete(*self.tabla.get_children())

        r = resultados["A*"]
        if r is None:
            self.ultimo, self.trayectoria = None, []
            self.resumen.config(text="✗ No hay solución: la gasolina no alcanza o la meta quedó incomunicada.")
            self.lbl_paso.config(text="Paso 0 / 0")
            self.dibujar_mapa()
            return

        self.ultimo = r
        self.trayectoria = r["nodo"].trayectoria()
        for i, paso in enumerate(r["camino"], 1):
            self.txt_plan.insert("end", f"{i:2}. {'[CARGA] ' if paso.startswith('Cargar') else ''}{paso}\n")
        optimo = resultados["UCS"]["costo"]
        for alg, x in resultados.items():
            ok = "Sí" if abs(x["costo"] - optimo) < 0.01 else "No"
            self.tabla.insert("", "end", values=(alg, f"{x['costo']:.2f}", x["expandidos"],
                                                 x["frontera_max"], f"{x['tiempo_ms']:.2f}", ok))
        self.txt_iter.insert("end", "\n".join(iteraciones))
        self.resumen.config(text=f"Gasto total: ${r['costo']:.2f}   ·   Llega con {r['litros_finales']:.2f} L"
                                 f"   ·   h(inicio) = ${problema.heuristica(problema.inicio):.2f}"
                                 f"\nRuta: {' → '.join(lugares_del_plan(r['nodo']))}")
        self.ir_a(len(self.trayectoria) - 1)        # muestra el plan completo

    def ir_a(self, paso):
        """Muestra el estado del plan en el paso indicado."""
        if not self.trayectoria:
            return
        self.paso = max(0, min(paso, len(self.trayectoria) - 1))
        nodo = self.trayectoria[self.paso]
        accion = nodo.accion or "Estado inicial"
        self.lbl_paso.config(text=f"Paso {self.paso} / {len(self.trayectoria) - 1}:  {accion}"
                                  f"   ·   {nodo.estado[1]:.2f} L   ·   gastado ${nodo.g:.2f}")
        self.dibujar_mapa()

    def reproducir(self):
        """Avanza solo, un paso cada 0.8 s."""
        if not self.trayectoria:
            return
        self.ir_a(0)

        def siguiente():
            if self.paso < len(self.trayectoria) - 1:
                self.ir_a(self.paso + 1)
                self.after(800, siguiente)
        self.after(800, siguiente)

    def abrir_maps(self):
        if self.ultimo is None:
            messagebox.showinfo("Sin ruta", "Primero busca un plan.")
            return
        webbrowser.open(enlace_google_maps(self.ultimo["nodo"]))

    # ================================================================
    # DIBUJO DEL MAPA
    # ================================================================
    def dibujar_mapa(self):
        c = self.canvas
        c.delete("all")
        esc = self.escenario
        if esc is None:                                   # antes de la primera búsqueda
            esc = Escenario("", "", 0)
        hecho = self.trayectoria[:self.paso + 1]
        lugares_hechos = [n.estado[0] for n in hecho]
        lugares_todos = [n.estado[0] for n in self.trayectoria]
        tramos_hechos = {frozenset(p) for p in zip(lugares_hechos, lugares_hechos[1:]) if p[0] != p[1]}
        tramos_plan = {frozenset(p) for p in zip(lugares_todos, lugares_todos[1:]) if p[0] != p[1]}
        cerrados = {frozenset(t) for t in esc.tramos_cerrados}
        km_esp = {frozenset(k): v for k, v in esc.km_especiales.items()}
        precios = {**PRECIOS_BASE, **esc.precios_especiales}

        # Cargas ya realizadas hasta este paso
        cargas = {}
        for n in hecho:
            if n.accion.startswith("Cargar"):
                cargas[n.estado[0]] = n.accion.split(" en ")[0].replace("Cargar ", "+")

        # Tramos
        for a, b, km in TRAMOS:
            (x1, y1), (x2, y2) = POSICIONES[a], POSICIONES[b]
            par = frozenset((a, b))
            if par in cerrados:
                c.create_line(x1, y1, x2, y2, fill=NEGRO, dash=(6, 4), width=2)
                c.create_text((x1 + x2) / 2, (y1 + y2) / 2 - 12, text="CERRADO", font=("Arial", 8, "bold"))
                continue
            if par in tramos_hechos:
                color, ancho, guion = NEGRO, 5, None          # ya recorrido
            elif par in tramos_plan:
                color, ancho, guion = "#555555", 3, (8, 4)    # falta recorrer
            else:
                color, ancho, guion = GRIS, 2, None
            c.create_line(x1, y1, x2, y2, fill=color, width=ancho, dash=guion)
            dx, dy = x2 - x1, y2 - y1                       # etiqueta fuera de la línea
            largo = (dx * dx + dy * dy) ** 0.5
            nx, ny = -dy / largo, dx / largo
            if ny > 0:
                nx, ny = -nx, -ny
            c.create_text((x1 + x2) / 2 + nx * 14, (y1 + y2) / 2 + ny * 14,
                          text=f"{km_esp.get(par, km)} km", font=("Arial", 8),
                          fill=NEGRO if par in tramos_plan else "#666666")

        # Nodos
        for clave, (x, y) in POSICIONES.items():
            es_meta, es_inicio = clave == esc.meta, clave == esc.inicio
            relleno = NEGRO if es_meta else ("white" if clave in lugares_todos else GRIS_CLARO)
            texto = "white" if es_meta else NEGRO
            borde = NEGRO if (clave in lugares_todos or es_meta) else GRIS
            c.create_rectangle(x - 36, y - 17, x + 36, y + 17, fill=relleno, outline=borde,
                               width=3 if es_inicio else (2 if clave in lugares_todos else 1))
            c.create_text(x, y - 6, text=clave, font=("Arial", 9, "bold"), fill=texto)
            if es_meta or es_inicio:
                c.create_text(x, y + 26, text="META" if es_meta else "INICIO", font=("Arial", 8, "bold"))
            sub = f"${precios[clave]:.2f}" if clave in precios else NOMBRES[clave].split(" (")[0][:14]
            c.create_text(x, y + 7, text=sub, font=("Arial", 8), fill=texto)
            if clave in cargas:
                c.create_text(x + 30, y - 26, text=cargas[clave], font=("Arial", 10, "bold"))

        # El Aveo: en el lugar del paso actual (o en el inicio)
        lugar = hecho[-1].estado[0] if hecho else esc.inicio
        x, y = POSICIONES[lugar]
        self._carro(x - 31, y - 52)
        if hecho:
            c.create_text(x + 52, y - 40, text=f"{hecho[-1].estado[1]:.2f} L", font=("Arial", 9, "bold"))

    def _carro(self, x, y):
        """Dibuja un Aveo blanco (vista lateral) con figuras simples."""
        c = self.canvas
        c.create_polygon(x, y + 22, x + 4, y + 14, x + 16, y + 12, x + 22, y + 4, x + 42, y + 4,
                         x + 50, y + 12, x + 60, y + 14, x + 62, y + 22, fill="white",
                         outline=NEGRO, width=2)
        c.create_polygon(x + 19, y + 12, x + 24, y + 7, x + 31, y + 7, x + 31, y + 12,
                         fill="#D6DCE0", outline=NEGRO)
        c.create_polygon(x + 34, y + 7, x + 41, y + 7, x + 47, y + 12, x + 34, y + 12,
                         fill="#D6DCE0", outline=NEGRO)
        for cx in (x + 15, x + 49):
            c.create_oval(cx - 6, y + 17, cx + 6, y + 29, fill="#2B2B2B", outline=NEGRO)
            c.create_oval(cx - 2, y + 21, cx + 2, y + 25, fill="#CFCFCF", outline="")


if __name__ == "__main__":
    Aplicacion().mainloop()
