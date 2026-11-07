#!/usr/bin/env python3
"""Comparacion simple por sexo con los datos exportados en data_export/csv/.

No inventa tiempos: la base no guarda marcas. Lo que hace es usar la velocidad
por cuadro (frame_metrics.speed, m/s) para estimar tiempo = distancia / velocidad.

Uso:  python3 scripts/analisis_sexo.py
Salida: data_export/analisis_sexo.csv y data_export/analisis_sexo.md
"""
import csv
import statistics as st
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "data_export"
CSV = BASE / "csv"
MIN_FRAMES_MOVIENDO = 30      # menos que esto = el clip no muestra la carrera
V_MOVIMIENTO = 0.5            # m/s: debajo de esto el atleta esta quieto


def load(name):
    with open(CSV / name) as f:
        return list(csv.DictReader(f))


def percentil(xs, q):
    if not xs:
        return 0.0
    xs = sorted(xs)
    return xs[int(round((len(xs) - 1) * q))]


def main():
    frames = defaultdict(list)
    for r in load("frame_metrics.csv"):
        frames[int(r["analysis_id"])].append(float(r["speed"]))

    metrics = {int(m["analysis_id"]): m for m in load("metrics.csv")}
    analyses = {int(a["id"]): a for a in load("analyses.csv")}
    videos = {int(v["id"]): v for v in load("videos.csv")}
    tests = {int(t["id"]): t for t in load("tests.csv")}
    athletes = {int(a["id"]): a for a in load("athletes.csv")}

    # ---- nivel 1: por analisis ----
    por_analisis = []
    for aid, speeds in sorted(frames.items()):
        moviendo = [s for s in speeds if s > V_MOVIMIENTO]
        if len(moviendo) < MIN_FRAMES_MOVIENDO:
            continue
        video = videos[int(analyses[aid]["video_id"])]
        test = tests[int(video["test_id"])]
        atleta = athletes[int(test["athlete_id"])]
        v_media = st.mean(moviendo)
        v_p90 = percentil(moviendo, 0.90)
        por_analisis.append({
            "analysis_id": aid,
            "atleta_id": atleta["id"],
            "atleta": f"{atleta['first_name']} {atleta['last_name']}",
            "sexo": atleta["gender"],
            "edad": int(atleta["age"]),
            "distancia_m": int(test["distance"]),
            "tecnica": test["technique"],
            "cuadros_movimiento": len(moviendo),
            "v_media_ms": round(v_media, 2),
            "v_p90_ms": round(v_p90, 2),
            "v_max_metrics": round(float(metrics[aid]["maximum_speed"]), 2) if aid in metrics else "",
            "tiempo_estimado_s": round(int(test["distance"]) / v_media, 2) if v_media else "",
        })

    # ---- nivel 2: por atleta (mejor analisis valido) ----
    por_atleta = {}
    for r in por_analisis:
        prev = por_atleta.get(r["atleta_id"])
        if prev is None or r["v_p90_ms"] > prev["v_p90_ms"]:
            por_atleta[r["atleta_id"]] = r

    # ---- nivel 3: por sexo ----
    grupos = defaultdict(list)
    for r in por_atleta.values():
        grupos[r["sexo"]].append(r)

    lineas = []
    lineas.append("| Sexo | Atletas | Vel. media (m/s) | Vel. p90 (m/s) | Tiempo est. 10 m (s) |")
    lineas.append("|---|---|---|---|---|")
    resumen = {}
    for sexo in ("Masculino", "Femenino", "Otro", "No especificado"):
        rs = grupos.get(sexo, [])
        if not rs:
            continue
        v_media = st.mean(r["v_media_ms"] for r in rs)
        v_p90 = st.mean(r["v_p90_ms"] for r in rs)
        tiempos = [r["tiempo_estimado_s"] for r in rs
                   if r["distancia_m"] == 10 and r["tiempo_estimado_s"] != ""]
        t_est = f"{st.mean(tiempos):.2f}" if tiempos else "—"
        resumen[sexo] = {"n": len(rs), "v_media": v_media, "tiempo_10m": st.mean(tiempos) if tiempos else None}
        lineas.append(f"| {sexo} | {len(rs)} | {v_media:.2f} | {v_p90:.2f} | {t_est} |")

    detalle = ["", "| Atleta | Sexo | Edad | Dist. | Cuadros | Vel. media | Vel. p90 | Tiempo est. |",
               "|---|---|---|---|---|---|---|---|"]
    for r in sorted(por_atleta.values(), key=lambda x: -x["v_media_ms"]):
        detalle.append(f"| {r['atleta']} | {r['sexo']} | {r['edad']} | {r['distancia_m']} m | "
                       f"{r['cuadros_movimiento']} | {r['v_media_ms']} | {r['v_p90_ms']} | "
                       f"{r['tiempo_estimado_s']} s |")

    # ---- salidas ----
    salida = BASE / "analisis_sexo.csv"
    with open(salida, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(por_atleta.values().__iter__().__next__().keys()))
        w.writeheader()
        for r in sorted(por_atleta.values(), key=lambda x: -x["v_media_ms"]):
            w.writerow(r)

    md = BASE / "analisis_sexo.md"
    md.write_text(
        "# Velocidad por sexo (estimada, no cronometrada)\n\n"
        f"Analisis con evidencia suficiente: {len(por_analisis)} · atletas: {len(por_atleta)}\n\n"
        "## Resumen\n\n" + "\n".join(lineas) + "\n\n"
        "## Por atleta (mejor analisis de cada uno)\n" + "\n".join(detalle) + "\n\n"
        "> `tiempo_estimado_s` = distancia / velocidad media en movimiento. No es una marca real:\n"
        "> la base no guarda tiempos y cada clip cubre un tramo distinto de la carrera.\n"
    )

    print("\n".join(lineas))
    print(f"\nAtletas: {len(por_atleta)} de {len(athletes)} · analisis utiles: {len(por_analisis)}")
    print(f"Escrito: {salida} y {md}")


if __name__ == "__main__":
    main()
