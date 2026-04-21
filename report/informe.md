# Informe breve: simulación SIR 2-D secuencial y paralela

## 1. Introducción

Este proyecto estudia la propagación de una epidemia sobre una grilla bidimensional de `1000 x 1000` celdas, equivalente a una población de un millón de individuos. Cada individuo evoluciona diariamente entre los estados susceptible, infectado, recuperado y fallecido. El objetivo principal fue implementar una versión secuencial correcta, una versión paralela que acelere la actualización diaria mediante partición por bloques y ghost cells, y un conjunto de experimentos de desempeño orientados a strong scaling.

El problema es adecuado para paralelización porque la actualización de cada celda depende solamente del estado del día anterior en su vecindad local. Esto permite dividir la grilla en subdominios independientes y sincronizar únicamente la información de borde entre bloques.

## 2. Modelo matemático

Sea `X_t(i, j)` el estado de la celda `(i, j)` en el día `t`. Se utiliza vecindad de Moore de ocho vecinos. Si `N_t(i, j)` representa el número de vecinos infectados de `(i, j)` en el día `t`, entonces para un individuo susceptible:

`P(X_{t+1}(i, j) = I | X_t(i, j) = S) = 1 - (1 - beta)^{N_t(i, j)}`

Esta ecuación modela contagios independientes por vecino infectado. Para un individuo infectado:

- `P(X_{t+1} = D | X_t = I) = mu`
- `P(X_{t+1} = R | X_t = I, no muerte) = gamma`
- `P(X_{t+1} = I) = 1 - mu - gamma` de manera implícita

Los estados recuperado y fallecido son absorbentes. La métrica epidemiológica reportada es una aproximación de `R_t`:

`R_t = nuevas_infecciones_t / infectados_activos_t`

También se mantiene el conteo de infectados acumulados:

`I_acum(t) = I_acum(t-1) + nuevas_infecciones_t`

## 3. Implementación secuencial

La versión secuencial fue desarrollada en Python con `numpy`. En lugar de iterar celda por celda desde Python, se aprovechan operaciones vectorizadas para:

- construir una máscara de infectados,
- contar vecinos mediante sumas de ventanas desplazadas,
- calcular probabilidades de transición para todas las celdas en bloque,
- aplicar las reglas de estado en una actualización síncrona.

Para garantizar reproducibilidad, la aleatoriedad no depende del orden de ejecución. Se implementó un generador determinista por celda y por día usando una mezcla hash de la coordenada, el día y la semilla global. Esto permite comparar de forma exacta la salida secuencial contra la paralela.

## 4. Implementación paralela

La versión paralela divide la grilla por bloques de filas. Si se ejecuta con p workers, cada worker recibe un subarreglo contiguo. Para computar correctamente las celdas del borde del subdominio, cada bloque lee una fila fantasma superior y una inferior tomadas de la grilla global del día anterior. Estas ghost cells permiten contar vecinos sin depender de lecturas adicionales durante la actualización local.

La ejecución paralela utiliza dos arreglos principales:

- `prev`: estado del día `t`
- `next`: estado del día `t + 1`

Cada worker:

1. toma su bloque local más las ghost cells,
2. actualiza únicamente sus filas internas,
3. escribe el resultado en la región correspondiente de `next`,
4. devuelve estadísticas parciales.

En esta versión se usó `ThreadPoolExecutor`, lo que permite mantener una implementación portable en el entorno disponible y conservar la descomposición por bloques exigida por la rúbrica.

Las estadísticas globales se obtienen mediante reducción de los resultados parciales. En particular, se agregan:

- susceptibles,
- infectados,
- recuperados,
- fallecidos,
- nuevas infecciones,
- infectados acumulados,
- aproximación de `R_t`.

## 5. Validación

La validez funcional se comprobó con un caso pequeño reproducible, ejecutando ambas versiones con la misma semilla. Gracias al esquema de números aleatorios determinista, se espera igualdad exacta en:

- la grilla final,
- los conteos diarios,
- el CSV de estadísticas.

El script `scripts/validate_small_case.py` automatiza esta comparación. 

## 6. Visualización

Para facilitar el análisis cualitativo del brote, cada ejecución puede capturar frames periódicos del estado de la grilla. El script `scripts/make_animation.py` construye una animación GIF side-by-side entre la versión secuencial y la paralela. Esto permite verificar visualmente que ambas siguen la misma dinámica epidémica y resaltar que la diferencia principal está en el tiempo de ejecución, no en el comportamiento del modelo.

 