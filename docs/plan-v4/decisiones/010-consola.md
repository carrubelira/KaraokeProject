# 010 · La consola: control de emisión, alta por enlace y una cola por pantalla

- **Fecha**: 21/11/2026
- **Estado**: aceptada (sustituye a la interfaz de `007-control` y al globo de `009-globo`)
- **Afecta a**: web, servidor (cola de tareas, colas, eventos), worker (análisis, registro,
  telemetría), reproductor (cola, dispositivos, errores)

## Contexto

La primera prueba real en el equipo (RTX 4080, Windows) sacó a la luz varios problemas:

- **Una tarea terminada volvía a ejecutarse.** Un informe de progreso que llegaba después de
  `complete` devolvía la tarea a `running`; su lease caducaba ("The worker stopped answering") y
  se repetía. La interfaz, además, se quedaba con un estado viejo para siempre.
- **Saídas daba 500.** El reproductor informaba dos salidas de audio con el mismo id (dos
  monitores iguales en la misma gráfica) y la lista con clave reventaba.
- **Añadir sin playlist activa no hacía nada**, pero decía «engadido».
- **El alta era torpe.** Un formulario con muchos campos antes de saber qué canción era.
- **Del worker no se veía nada.** El log del proceso hijo se borraba, los `note` se perdían y en
  Windows no había CPU ni RAM.

El usuario pidió rehacer la interfaz desde cero, inmersiva y profesional, con efectos Three.js
que respondan al estado de workers y reproductores. Eligió estas opciones:

- **Estética**: consola de broadcast.
- **Identificación**: AcoustID + MusicBrainz.
- **Colas**: una por pantalla.
- **Idiomas**: galego e inglés.
- **Globo**: fuera.
- **Archivos locales**: como entrada secundaria.

## Decisión

### Consola

- **Lenguaje visual.** Una sala de control nocturna:
  - paneles de cristal oscuro enmarcados como unidades de rack;
  - pilotos tally con un significado fijo (rojo en antena, verde preparado, ámbar a la espera o
    aviso, cian en movimiento);
  - Martian Mono para los datos.
- **Estructura.** Tres piezas fijas:
  - una franja superior: pantalla que se maneja, ON AIR, reloj y salud del sistema;
  - un rail de secciones;
  - un deck inferior con el transporte y dos encoders (tono y volumen), siempre a mano.
- **Fondo Three.js.** Un campo de señal:
  - el suelo de puntos respira con el trabajo;
  - cada worker es un núcleo que gira con su GPU y lanza partículas al hub mientras trabaja;
  - cada pantalla es un núcleo que late en rojo en antena.

  Es decorativo: todo lo que muestra está escrito en la interfaz. Descansa con la pestaña
  oculta, con «Efectos» y con el movimiento reducido del sistema.
- **Sin `backdrop-filter` ni `mix-blend-mode`.** Algunos navegadores dejan de componer el lienzo
  WebGL de detrás si se usan.
- **Secciones.** Directo, Engadir, Traballos, Biblioteca, Nodos, Saídas, Axustes y el editor.
- **El monitor de programa** de Directo pinta la letra de la canción en antena con la posición
  del reproductor, como un monitor de confianza.

### Alta por enlace: analizar antes, confirmar después

El DAG pasa a ser `fetch → analyze → make` (o `analyze → make` para un archivo).

- **`analyze`** (en el worker, sin GPU) hace estos pasos:
  - lee la página o las etiquetas;
  - saca la huella Chromaprint;
  - consulta AcoustID y MusicBrainz (idioma de la letra y portada);
  - busca en LRCLIB.
- **Revisión.** Al acabar, el job queda en `review` y su `make` en `held` hasta que el operador
  confirma o corrige título, artista, idioma y letra (`POST /api/jobs/{id}/confirm`). Puede pedir
  que, al terminar, la canción vaya a la cola de una pantalla (`queue_on`); lo hace el servidor,
  aunque se cierre la pestaña.
- **Sin clave de AcoustID** (`KARAOKE_ACOUSTID_KEY` en el worker) la huella no se consulta y la
  revisión lo dice.
- **`auto_confirm`** (desactivado por defecto) sigue sin revisión si la análisis está segura
  (≥ 0,85).

### Una cola por pantalla

- **Fuera las playlists.** Desaparecen como concepto del operador. Cada reproductor tiene su
  `Queue` desde que se enrola; la migración 2 convierte en cola la playlist a la que apuntaba.
- **Añadir siempre funciona.** `POST …/queue/items` añade al final de lo que haya, sin conflicto
  de versión.
- **Reordenar o quitar** reescribe la cola con versión optimista.

### Estado fiable

**Cola de tareas.** Se refuerza en varios puntos:

- `progress` rechaza tareas que no estén `leased` o `running`;
- `complete` limpia el lease y el error, y publica el evento `task`;
- `complete` no puede revivir un job cancelado;
- los reintentos respetan la pausa;
- un fallo de `on_job_done` marca el job como `failed` en vez de dejarlo activo.

**Worker.** Cada tarea tiene un `Feed`, un solo emisor en orden que se vacía antes de
`complete` o `fail`.

- La telemetría trae CPU y RAM (psutil).
- El log se emite en vivo y se sube entero al terminar.
- Las barras de progreso con `\r` se compactan en una línea.

**Eventos.** Todos llevan `seq`. El cliente detecta huecos y silencio, y reabre la conexión, que
trae un snapshot nuevo. Los nodos entran por eventos, no por sondeo.

**Reproductor.**

- Los ids de audio repetidos reciben `#2`, `#3`…
- Su estado incluye `errors`: salida que no abre o se pierde, canción que no carga, mestra
  perdida.

## Consecuencias

- **Lo que se borra:**
  - el globo y su script de mapa;
  - el castellano de la interfaz;
  - las vistas y el CSS `ctl-*`;
  - las rutas de playlists;
  - los tipos OpenAPI generados que nadie importaba.

  `knip` vigila que no quede código muerto.
- **Tipos escritos a mano.** La API sigue tipada a mano en `src/lib/control/types.ts`: la mayoría
  de rutas devuelven diccionarios y los tipos generados no aportaban nada.
- **Pendiente:**
  - ETA por fase (hoy, por tarea);
  - un selector de portadas;
  - probar AcoustID con una clave real.
