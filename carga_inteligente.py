# =====================================================================
#   CARGA INTELIGENTE  ·  MODO CONSOLA
#   Muestra en la terminal los resultados del módulo busqueda.py
#
#   Fundamentos de Inteligencia Artificial · 7° "C" · Corte 2
#   Carlos Andrés Mazariegos Laguna (243790)
#   Axel Rodrigo Cuc López          (243702)
#
#   Ejecutar:          python carga_inteligente.py
#   Los 4 escenarios:  python carga_inteligente.py --todos
#   Interfaz gráfica:  python interfaz.py
# =====================================================================

import sys
import webbrowser
from urllib.parse import quote_plus   # para armar el enlace de Google Maps

from busqueda import ESCENARIOS, NOMBRES, Escenario, lugares_del_plan, resolver


CARRO = r"""
            ______________
           /   |      |   \___
     _____/____|______|_______\___
    |  _                   _      |=
    '-(_)-----------------(_)-----'     CARGA INTELIGENTE · Aveo 2015
"""


def enlace_google_maps(nodo):
    """Arma un enlace de Google Maps con la ruta elegida y sus paradas."""
    lugares = [NOMBRES[l] + ", Chiapas" for l in lugares_del_plan(nodo)]
    origen, destino, paradas = lugares[0], lugares[-1], lugares[1:-1]
    url = ("https://www.google.com/maps/dir/?api=1&travelmode=driving"
           f"&origin={quote_plus(origen)}&destination={quote_plus(destino)}")
    if paradas:
        url += "&waypoints=" + quote_plus("|".join(paradas))
    return url


def mostrar_plan(r):
    print("\n  Plan óptimo encontrado por A*:")
    for i, paso in enumerate(r["camino"], 1):
        marca = "⛽" if paso.startswith("Cargar") else "→"
        print(f"   {i:2}. {marca} {paso}")
    print(f"\n   Gasto total: ${r['costo']:.2f}   |   "
          f"Llega a la meta con {r['litros_finales']:.2f} L")
    print(f"   Ruta: {' → '.join(lugares_del_plan(r['nodo']))}")


def mostrar_comparacion(resultados):
    optimo = resultados["UCS"]["costo"]
    linea = "   " + "-" * 66
    print("\n  Comparación de algoritmos:")
    print(linea)
    print(f"   {'Algoritmo':<10}{'Gasto ($)':>10}{'Expandidos':>12}"
          f"{'Frontera máx.':>15}{'Tiempo ms':>11}{'Óptimo':>8}")
    print(linea)
    for nombre, r in resultados.items():
        ok = "Sí" if abs(r["costo"] - optimo) < 0.01 else "No"
        print(f"   {nombre:<10}{r['costo']:>10.2f}{r['expandidos']:>12}"
              f"{r['frontera_max']:>15}{r['tiempo_ms']:>11.2f}{ok:>8}")
    print(linea)


def guardar_grafica(resultados, archivo):
    """Gráfica de barras de estados expandidos (requiere matplotlib)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("   (Instala matplotlib para la gráfica: pip install matplotlib)")
        return
    nombres = list(resultados)
    valores = [resultados[n]["expandidos"] for n in nombres]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    barras = ax.bar(nombres, valores, color=["#BDBDBD", "#8C8C8C", "#5E5E5E", "#1A1A1A"],
                    edgecolor="black", linewidth=0.8, width=0.6)
    for b, v in zip(barras, valores):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v}", ha="center", va="bottom",
                fontsize=10, fontweight="bold")
    ax.set_ylabel("Estados expandidos")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", linestyle=":", alpha=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(archivo, dpi=200)
    plt.close(fig)
    print(f"   Gráfica guardada en: {archivo}")


def ejecutar(escenario, numero, ver_iteraciones=False, preguntar_mapa=True):
    print("\n" + "=" * 70)
    print(f"  ESCENARIO {escenario.nombre}")
    print(f"  {escenario.descripcion}")
    print("=" * 70)
    iteraciones = [] if ver_iteraciones else None
    problema, resultados = resolver(escenario, iteraciones)
    print(f"   Litros mínimos para llegar: {problema.litros_minimos.get(escenario.inicio, '—')} L"
          f"   |   h(inicio) = ${problema.heuristica(problema.inicio):.2f}")

    for alg, r in resultados.items():
        if r is None:
            print(f"\n   ✗ {alg}: no hay solución. La gasolina no alcanza "
                  "o la meta quedó incomunicada.")
            return None
    if ver_iteraciones:
        print("\n  Iteraciones de A*:")
        for linea in iteraciones:
            print("   " + linea)

    mostrar_plan(resultados["A*"])
    mostrar_comparacion(resultados)
    guardar_grafica(resultados, f"comparacion_escenario_{numero}.png")

    url = enlace_google_maps(resultados["A*"]["nodo"])
    print(f"\n   Ver la ruta en Google Maps:\n   {url}")
    if preguntar_mapa and input("   ¿Abrir en el navegador? (s/n): ").strip().lower() == "s":
        webbrowser.open(url)
    return resultados


def main():
    try:                                              # acentos y símbolos en cualquier consola
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    print(CARRO)
    print("  Ruta y repostaje: Chapultepec, Tuxtla Gutiérrez → UP Chiapas\n")

    if "--todos" in sys.argv:                         # modo para el reporte
        for i, esc in enumerate(ESCENARIOS, 1):
            ejecutar(esc, i, ver_iteraciones=(i == 1), preguntar_mapa=False)
        return

    for esc in ESCENARIOS:
        print(f"   {esc.nombre:<32} {esc.descripcion}")
    print("   5. Personalizado                 Tú eliges los litros iniciales.")
    opcion = input("\n  Elige un escenario (1-5) [Enter = 1]: ").strip() or "1"

    if opcion == "5":
        texto = input("  ¿Con cuántos litros sale el auto?: ").strip()
        litros = float(texto) if texto else 0.5
        escenario = Escenario("5. Personalizado", f"Sale con {litros} L.", litros)
    elif opcion in ("1", "2", "3", "4"):
        escenario = ESCENARIOS[int(opcion) - 1]
    else:
        print("  Opción no válida.")
        return

    ver = input("  ¿Mostrar las iteraciones de A*? (s/n) [Enter = n]: ").strip().lower() == "s"
    ejecutar(escenario, opcion, ver_iteraciones=ver)


if __name__ == "__main__":
    main()
