# =====================================================================
#   CARGA INTELIGENTE · MÓDULO DE BÚSQUEDA
#   Aquí está SOLO el modelo del problema y los algoritmos de búsqueda.
#   No imprime nada ni dibuja nada: eso lo hacen
#   carga_inteligente.py (consola) e interfaz.py (ventana).
#
#   Fundamentos de Inteligencia Artificial · 7° "C" · Corte 2
#   Carlos Andrés Mazariegos Laguna (243790)
#   Axel Rodrigo Cuc López          (243702)
# =====================================================================

import heapq            # cola de prioridad: siempre saca el elemento más pequeño
import time             # para medir el tiempo de cada algoritmo
from dataclasses import dataclass, field


# ---------------------------------------------------------------------
# 1. DATOS DEL MAPA
#    Distancias tomadas de Google Maps y precios de gasolina Magna.
# ---------------------------------------------------------------------

RENDIMIENTO = 14.0              # km por litro (Chevrolet Aveo 2015, supuesto)
CAPACIDAD = 45.0                # litros que le caben al tanque
CARGAS_POSIBLES = (1, 2, 3)     # litros que se pueden cargar en cada parada
ALGORITMOS = ("BFS", "UCS", "Greedy", "A*")

# Nombre completo de cada nodo del grafo
NOMBRES = {
    "CHAP": "Chapultepec (casa)",
    "T1": "Gasolinera Terán Blvd. Belisario Domínguez",
    "T2": "Pemex 1a Av. Sur Poniente",
    "T3": "Gasolinera Terán Calz. Emiliano Zapata",
    "T4": "Pemex Santa Elena (Libramiento Sur Pte.)",
    "J1": "Gasolinera Gamboa (Calz. Samuel León Brindis)",
    "J2": "Gasolinera El Jobo (km 5.5)",
    "K1": "Pemex Blvd. Ángel Albino Corzo",
    "K2": "Pemex Ribera Las Flechas",
    "K3": "Gasolinera Tepetchia",
    "SUCH": "Gasolinera entrada de Suchiapa",
    "UP": "UP Chiapas",
}

# Precio normal de la Magna ($/L). Los nodos que no están aquí no tienen gasolinera.
PRECIOS_BASE = {
    "T1": 23.99, "T2": 23.89, "T3": 23.79, "T4": 23.69,
    "J1": 23.89, "J2": 24.09,
    "K1": 23.79, "K2": 23.76, "K3": 23.76,
    "SUCH": 23.99,
}

# Tramos de calle (A, B, km). Se puede circular en ambos sentidos.
TRAMOS = [
    ("CHAP", "T1", 3.0), ("T1", "T2", 1.5), ("T2", "T3", 1.2),          # Ruta Terán
    ("T3", "T4", 2.4), ("T4", "SUCH", 13.0),
    ("CHAP", "J1", 9.0), ("J1", "J2", 8.4), ("J2", "SUCH", 15.0),       # Ruta El Jobo
    ("CHAP", "K1", 12.0), ("K1", "K2", 6.5), ("K2", "K3", 3.6),          # Ruta Chiapa
    ("K3", "SUCH", 34.0),
    ("T3", "J1", 5.0),                                                   # Conexión Terán–Jobo
    ("SUCH", "UP", 3.0),                                                 # Tramo final común
]


# ---------------------------------------------------------------------
# 2. ESCENARIOS
#    Cada escenario puede cambiar el inicio, la meta, los litros,
#    los precios, los km, el rendimiento o cerrar tramos.
# ---------------------------------------------------------------------

@dataclass
class Escenario:
    nombre: str
    descripcion: str
    litros_iniciales: float
    precios_especiales: dict = field(default_factory=dict)   # {nodo: precio nuevo}
    tramos_cerrados: list = field(default_factory=list)      # [(A, B), ...]
    km_especiales: dict = field(default_factory=dict)        # {(A, B): km nuevos}
    rendimiento: float = RENDIMIENTO                         # km/L del auto
    capacidad: float = CAPACIDAD                             # litros del tanque
    inicio: str = "CHAP"                                     # de dónde sale
    meta: str = "UP"                                         # a dónde quiere llegar


ESCENARIOS = [
    Escenario("1. En reserva",
              "Sale con 0.5 L, casi vacío. Tiene que cargar en el camino.",
              0.5),
    Escenario("2. Tanque suficiente",
              "Sale con 5 L. Le alcanza para todo el viaje.",
              5.0),
    Escenario("3. Obra en el Libramiento Sur",
              "Sale con 0.5 L y el tramo Calz. Emiliano Zapata – Santa Elena está cerrado.",
              0.5, tramos_cerrados=[("T3", "T4")]),
    Escenario("4. Promoción en El Jobo",
              "Sale con 0.5 L y la Gasolinera Gamboa tiene la Magna a $21.49.",
              0.5, precios_especiales={"J1": 21.49}),
]


# ---------------------------------------------------------------------
# 3. EL PROBLEMA DE BÚSQUEDA
#    Un ESTADO es la tupla (lugar, litros, ya_cargo_aqui).
# ---------------------------------------------------------------------

class Problema:
    def __init__(self, escenario):
        """Prepara todo lo que necesita la búsqueda a partir de un Escenario."""
        self.escenario = escenario
        self.precios = {**PRECIOS_BASE, **escenario.precios_especiales}
        self.rendimiento = escenario.rendimiento
        self.capacidad = escenario.capacidad
        self.meta = escenario.meta
        self.km = {frozenset(k): v for k, v in escenario.km_especiales.items()}
        self.grafo = self._construir_grafo(escenario.tramos_cerrados)
        self.litros_minimos = self._calcular_litros_minimos()
        self.precio_minimo = min(self.precios.values())
        self.inicio = (escenario.inicio, escenario.litros_iniciales, False)

    def _construir_grafo(self, cerrados):
        """Lista de tramos -> diccionario {lugar: {vecino: litros}}."""
        cerrados = {frozenset(t) for t in cerrados}
        grafo = {n: {} for n in NOMBRES}
        for a, b, km in TRAMOS:
            if frozenset((a, b)) in cerrados:         # tramo cerrado: no se agrega
                continue
            km = self.km.get(frozenset((a, b)), km)   # km editados (si los hay)
            litros = round(km / self.rendimiento, 2)  # km ÷ rendimiento = litros
            grafo[a][b] = litros
            grafo[b][a] = litros
        return grafo

    def _calcular_litros_minimos(self):
        """Dijkstra desde la META: litros mínimos para llegar desde cada lugar."""
        minimos, frontera = {}, [(0.0, self.meta)]
        while frontera:
            litros, lugar = heapq.heappop(frontera)
            if lugar in minimos:
                continue
            minimos[lugar] = round(litros, 2)
            for vecino, gasto in self.grafo[lugar].items():
                heapq.heappush(frontera, (litros + gasto, vecino))
        return minimos

    def es_meta(self, estado):
        """True si el auto está en el lugar meta (los litros ya son >= 0)."""
        return estado[0] == self.meta

    def sucesores(self, estado):
        """Genera (acción, nuevo_estado, costo) para cada acción válida."""
        lugar, litros, ya_cargo = estado

        # Acción AVANZAR: cuesta $0, pero gasta litros. Solo si alcanza la gasolina.
        for vecino, gasto in self.grafo[lugar].items():
            restante = round(litros - gasto, 2)
            if restante >= 0:
                yield f"Ir a {NOMBRES[vecino]}", (vecino, restante, False), 0.0

        # Acción CARGAR: solo en gasolinera, una vez por parada y sin rebasar el tanque.
        if lugar in self.precios and not ya_cargo:
            for q in CARGAS_POSIBLES:
                if litros + q <= self.capacidad:
                    costo = round(q * self.precios[lugar], 2)
                    yield (f"Cargar {q} L en {NOMBRES[lugar]} (${costo:.2f})",
                           (lugar, round(litros + q, 2), True), costo)

    def heuristica(self, estado):
        """h = litros que faltan × precio más barato. Nunca exagera (ADMISIBLE)."""
        lugar, litros, _ = estado
        if lugar not in self.litros_minimos:          # desde aquí ya no se llega a la meta
            return float("inf")
        faltan = max(0.0, self.litros_minimos[lugar] - litros)
        return round(faltan * self.precio_minimo, 2)


# ---------------------------------------------------------------------
# 4. BÚSQUEDA GENERAL
#    Los 4 algoritmos comparten este código. Solo cambia la PRIORIDAD:
#      BFS -> pasos · UCS -> g · Greedy -> h · A* -> g + h
# ---------------------------------------------------------------------

@dataclass
class Nodo:
    estado: tuple
    g: float = 0.0                 # pesos gastados desde el inicio
    pasos: int = 0                 # acciones realizadas
    padre: "Nodo" = None           # nodo del que venimos
    accion: str = ""               # acción que nos trajo aquí

    def camino(self):
        """Reconstruye la lista de acciones siguiendo a los padres."""
        acciones, nodo = [], self
        while nodo.padre is not None:
            acciones.append(nodo.accion)
            nodo = nodo.padre
        return acciones[::-1]

    def trayectoria(self):
        """Lista de nodos desde la raíz hasta este (para ejecutar paso a paso)."""
        nodos, nodo = [], self
        while nodo is not None:
            nodos.append(nodo)
            nodo = nodo.padre
        return nodos[::-1]


def prioridad(algoritmo, nodo, h):
    """Número con el que se ordena la frontera según el algoritmo."""
    return {"BFS": nodo.pasos, "UCS": nodo.g, "Greedy": h}.get(algoritmo, nodo.g + h)


def buscar(problema, algoritmo, registro=None):
    """Búsqueda general con frontera ordenada y cycle checking.
    registro: lista opcional donde se guarda cada iteración (texto)."""
    raiz = Nodo(problema.inicio)
    frontera = [(0, 0, raiz)]          # (prioridad, desempate, nodo)
    expandidos = set()                 # cycle checking
    contador, frontera_max = 0, 1
    t0 = time.perf_counter()

    while frontera:
        _, _, nodo = heapq.heappop(frontera)          # 1) sacar el de menor prioridad
        if nodo.estado in expandidos:
            continue
        expandidos.add(nodo.estado)

        if registro is not None:
            h = problema.heuristica(nodo.estado)
            lugar, litros, _ = nodo.estado
            registro.append(f"It. {len(expandidos):3}: ({lugar:>4}, {litros:5.2f} L)"
                            f"  g = {nodo.g:6.2f}  h = {h:6.2f}  f = {nodo.g + h:6.2f}")

        if problema.es_meta(nodo.estado):             # 2) ¿es la meta? (al SACARLA)
            return {"costo": round(nodo.g, 2), "camino": nodo.camino(),
                    "expandidos": len(expandidos), "frontera_max": frontera_max,
                    "tiempo_ms": (time.perf_counter() - t0) * 1000,
                    "litros_finales": nodo.estado[1], "nodo": nodo}

        for accion, nuevo, costo in problema.sucesores(nodo.estado):   # 3) expandir
            if nuevo in expandidos:
                continue
            hijo = Nodo(nuevo, round(nodo.g + costo, 2), nodo.pasos + 1, nodo, accion)
            h = problema.heuristica(nuevo)
            if h == float("inf"):                     # callejón sin salida: se descarta
                continue
            contador += 1
            heapq.heappush(frontera, (prioridad(algoritmo, hijo, h), contador, hijo))
        frontera_max = max(frontera_max, len(frontera))

    return None                                       # frontera vacía: no hay solución


def resolver(escenario, registro=None):
    """Corre los 4 algoritmos sobre un escenario. Devuelve (problema, resultados).
    Las iteraciones que se guardan en 'registro' son las de A*."""
    problema = Problema(escenario)
    resultados = {alg: buscar(problema, alg, registro if alg == "A*" else None)
                  for alg in ALGORITMOS}
    return problema, resultados


def lugares_del_plan(nodo):
    """Lista de lugares por los que pasa el plan (sin repetir paradas)."""
    lugares = []
    for n in nodo.trayectoria():
        if not lugares or lugares[-1] != n.estado[0]:
            lugares.append(n.estado[0])
    return lugares
