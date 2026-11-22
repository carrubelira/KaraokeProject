# 010 · La consola: interfaz tradicional, alta por enlace y una cola por pantalla

- **Fecha**: 21/11/2026 (revisada el 22/11/2026: interfaz tradicional)
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

- **Estética**: consola de broadcast (primera versión; ver la revisión más abajo).
- **Identificación**: AcoustID + MusicBrainz.
- **Colas**: una por pantalla.
- **Idiomas**: galego e inglés.
- **Globo**: fuera.
- **Archivos locales**: como entrada secundaria.

## Decisión

### Consola

**Revisión del 22/11/2026.** La primera versión (sala de control de emisión con un campo de
partículas Three.js de fondo, franja ON AIR, rail y deck con encoders) resultó fea y confusa: las
partículas no aportaban nada, cada vista tenía su propio diseño y la de trabajos costaba
entenderla. El usuario pidió una interfaz tradicional, sin las tipografías de siempre ni
etiquetas de jerga, con Galicia solo en segundo plano. Eligió:

- **Tema**: oscuro sobrio (grises, un solo acento azul).
- **Tipografía**: IBM Plex Sans y IBM Plex Mono.
- **Galicia**: el perfil de la costa, tenue, detrás de la barra lateral y en los estados vacíos.

Queda así:

- **Estructura.** Una aplicación de escritorio corriente:
  - barra lateral con las secciones en palabras;
  - páginas hechas de cabecera, paneles y tablas;
  - barra de reproducción abajo: pantalla, qué suena, transporte, tono y volumen.
- **Una sola hoja de estilos** (`app.css`) con las piezas comunes (cabecera, panel, tabla,
  badge, botón, campo, pestañas, estado vacío, aviso). Las páginas solo añaden su maquetación.
- **Vocabulario llano.** «Equipos de procesado» y «Pantallas» en vez de workers y players,
  estados en palabras («En curso», «Agarda revisión», «Rematado», «Erro»), «Retirar» en vez de
  revocar.
- **Procesamento** es una tabla de canciones (estado, paso actual con su progreso, equipo,
  tiempo). Cada fila se despliega para ver los pasos, el motivo de un fallo con qué hacer y el
  registro de cada paso.
- **Secciones.** Reprodución, Biblioteca, Engadir canción, Procesamento, Equipos, Saídas,
  Axustes y el editor.
- **Fuera:** Three.js, el campo de partículas, los encoders, la franja ON AIR, el ajuste
  «Efectos» y las fuentes Figtree, Martian Mono y Unbounded.

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
