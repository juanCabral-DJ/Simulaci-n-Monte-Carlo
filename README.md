# Simulación SIR 2-D paralela

Proyecto para modelar un brote epidémico sobre una grilla de `1000 x 1000` celdas usando estados `S`, `I`, `R` y `D`, con versión secuencial y versión paralela por bloques con ghost cells.

## Estructura

- `sequential/`: ejecutable de la versión secuencial.
- `parallel/`: ejecutable de la versión paralela con `ThreadPoolExecutor`.
- `common/`: núcleo vectorizado compartido, estadísticas y renderizado.
- `scripts/`: validación, benchmark, gráfica de speed-up y animación.
- `results/`: salidas generadas por experimentos.
- `report/`: informe breve en Markdown.

## Modelo

Cada celda representa una persona en uno de cuatro estados:

- `0`: susceptible
- `1`: infectado
- `2`: recuperado
- `3`: fallecido

La actualización es diaria y síncrona. Para una celda susceptible con `n` vecinos infectados de Moore:

`P(contagio) = 1 - (1 - beta)^n`

Para una celda infectada:

- `P(muerte) = mu`
- `P(recuperación) = gamma`
- `P(seguir infectado) = 1 - mu - gamma` de forma implícita

`R_t` se aproxima como:

`R_t = nuevas_infecciones_dia / infectados_activos_dia_anterior`

En los CSV se expone también como `R0_proxy` para alinearlo con la rúbrica.

## Decisiones de implementación

- La versión secuencial usa operaciones vectorizadas con `numpy`.
- La versión paralela divide la grilla por bloques de filas.
- Cada bloque lee una fila fantasma superior e inferior para computar vecinos en los bordes.
- Los bloques se actualizan en paralelo sobre arreglos compartidos del mismo proceso, escribiendo en regiones disjuntas de la grilla siguiente.
- El generador aleatorio es determinista por celda y por día, por lo que secuencial y paralelo producen resultados idénticos con la misma semilla.

## Requisitos

Instalar dependencias:

```powershell
python -m pip install numpy pillow matplotlib imageio pandas
```

## Ejecución

Versión secuencial:

```powershell
python sequential/run_sequential.py --rows 1000 --cols 1000 --days 365 --stats-csv results/sequential/stats.csv --frames-dir results/sequential/frames --metadata-json results/sequential/summary.json
```

Versión paralela:

```powershell
python parallel/run_parallel.py --rows 1000 --cols 1000 --days 365 --workers 8 --stats-csv results/parallel/stats.csv --frames-dir results/parallel/frames --metadata-json results/parallel/summary.json
```

Validación caso pequeño:

```powershell
python scripts/validate_small_case.py
```

Strong scaling:

```powershell
python scripts/benchmark.py --rows 1000 --cols 1000 --days 365 --workers 1 2 4 8
python scripts/plot_speedup.py --input results/benchmark/strong_scaling.csv --output results/benchmark/speedup.png
```

Animación side-by-side:

```powershell
python scripts/make_animation.py --sequential-frames results/sequential/frames --parallel-frames results/parallel/frames --output results/animation/sir_side_by_side.gif
```

## Entregables cubiertos

- Código secuencial y paralelo en carpetas separadas.
- Validación reproducible con caso pequeño.
- CSV de tiempos y gráfica de speed-up.
- Animación comparando secuencial y paralelo.
- README e informe base en `report/informe.md`.

## Resultados ya generados en este repo

- Validación exacta: `results/validation/`
- Benchmark fuerte: `results/benchmark/strong_scaling.csv`
- Gráfica de speed-up: `results/benchmark/speedup.png`
- Frames y estadísticas secuenciales: `results/sequential/`
- Frames y estadísticas paralelas: `results/parallel/`
- Animación comparativa: `results/animation/sir_side_by_side.gif`

El benchmark generado en este entorno usó `256 x 256` celdas durante `120` días para terminar rápido y producir artefactos reproducibles. Para la entrega final de la rúbrica, conviene volver a correr los mismos scripts con `1000 x 1000` y `365` días.

## Campaña final 1000x1000 x 365 días

Artefactos finales ya generados:

- CSV benchmark: `results/final/benchmark/strong_scaling_1000x1000_365d.csv`
- Gráfica final: `results/final/benchmark/speedup_1000x1000_365d.png`
- Estadísticas secuenciales: `results/final/sequential/stats.csv`
- Estadísticas paralelas: `results/final/parallel/stats.csv`
- Animación final: `results/final/animation/sir_side_by_side_1000x1000_365d.gif`

Resumen de tiempos:

- Secuencial: `82.80 s`
- Paralelo 1 worker: `53.27 s`
- Paralelo 2 workers: `34.31 s`
- Paralelo 4 workers: `25.99 s`
- Paralelo 8 workers: `12.64 s`

Speed-up observado:

- `2 workers`: `2.41x`
- `4 workers`: `3.19x`
- `8 workers`: `6.55x`
