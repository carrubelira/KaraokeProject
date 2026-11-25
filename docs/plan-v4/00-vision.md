# Plan v4 · Arquitectura distribuida

> Fuente de verdad del plan v4 (19/11/2026). Sustituye a `docs/plan-v3/`. Si algo cambia, se
> cambia con una decisión escrita en `decisiones/` y se actualiza este documento en el mismo PR.
> Sin retrocompatibilidad con v3 en tiempo de ejecución.

## 1. Alcance

| Tema | Decisión |
|---|---|
| Red | Red local: servidor, pantallas y audio siempre en la misma LAN. **HTTP sin TLS** (`decisiones/011`) |
| Topología | Servidor y worker **pueden ser el mismo PC**, o estar separados; el audio sale del PC del servidor |
| Reproductor | **Uno por backend** (`decisiones/011`): el audio, en el backend (`kp-audio`, Rust), a 1 o 2 salidas; la imagen, en **pantallas web** sincronizadas (navegadores en Windows, Linux y macOS, y kioscos Tauri en Raspberry Pi) |
| Arranque | Ningún contenido suena hasta que lo ordena el operador |
| Workers | Linux y Windows nativos (sin WSL), GPU NVIDIA (CUDA), modelo *pull* |
| Micrófonos | Fuera del sistema: mezclador o monitor directo de la tarjeta |
| Tono | Se mantiene, aplicado en el reproductor a la voz guía y a la música |
| Medición | Solo por software: banco simulado (`decisiones/002`) y diagnóstico en el aparato |
| Globo de inicio | Se mantiene, de noche, con Galicia en su contexto geográfico real |
| Se mantienen | Editor de letra y tiempos (con mini reproductor web), exportación MP4 |
| Se descartan | PWA, modo fiesta, zonas de red, TLS |

La sincronía **entre todas las pantallas** y el audio es un requisito (`decisiones/011`): el
servidor publica la sesión con un ancla en su reloj monótono, `kp-audio` suena en ese instante y
cada pantalla dibuja cada fotograma para el instante en que se verá.

## 2. Piezas

```
 Control (web) ◄──WS/HTTP──► SERVIDOR ◄──pull──► WORKERS (Win/Linux, GPU)
                               │  ▲
                               │  └── CAS + cola + registro de nodos
                               ├──WS local──► kp-audio (DAC 1, DAC 2)
                               └──WS: hora + sesión──► PANTALLAS WEB × N
```

> Desde `decisiones/011`, el «reproductor» es el conjunto de `kp-audio` en el backend y las
> pantallas web. Donde este documento dice reproductor nativo con ventanas, manda la 011.

- **Servidor** (Python/FastAPI, nativo en Windows y Linux): fuente de verdad. No importa torch ni
  modelos, igual que en v3.
- **Worker** (Python, `packages/worker`): ejecuta tareas; reutiliza `packages/engine`.
- **Reproductor** (Rust, `player/`): obedece al servidor y reporta sus salidas y su estado.
- **Control** (`web/`, SvelteKit): interfaz de operador pensada para teclado.

## 3. Servidor

### Almacén por contenido (CAS)
- Blobs direccionados por SHA-256; un contenido es un manifiesto que referencia blobs.
- Entrega por HTTP con `Range`, verificación de hash y reanudación. Si el nodo está en el mismo PC,
  se entrega por ruta local o *hardlink*, no por HTTP a localhost.
- Sin recompresión de transporte para medios; zstd solo para JSON y subtítulos.
- Recolección de basura por referencias, papelera de 30 días, cuotas.

### Cola y planificador
- Persistente (SQLite), con *lease* y latido; si un worker muere, la tarea se reasigna.
- Prioridad (interactiva > lote), reintentos idempotentes, cancelar, pausar, fijar a un worker.
- Asignación por capacidades (SO, GPU, VRAM libre, modelos, `internet`) y por **afinidad de datos**
  (se prefiere el worker que ya tiene los blobs de entrada).
- Primera versión: tareas gruesas, `fetch → make → render (opcional)`, donde `make` es
  `karaoke_engine.make.make_package` tal cual. El DAG fino
  (`ingest → separar → transcribir → alinear → empaquetar`) solo se activa tras la fase 3 y con dos
  workers o más: hoy los pasos se pasan WAV grandes y en 4 GB solo cabe un modelo a la vez.
- Estados al control por WebSocket.

### Registro de nodos y seguridad
- Enrolado con token de un solo uso; ID estable y credencial por nodo.
- TLS siempre, con el certificado del servidor fijado al enrolar; igual por la LAN que por Tailscale.
- Las ACL de Tailscale (`tag:worker`, `tag:player`) son una capa extra, no la única.

Se reutiliza: `db.py`, `library.py`, `jobs/intake.py` (subidas en streaming), `jobs/progress.py`
(`Estimator`, ETA), la generación de OpenAPI. Se reescribe: `jobs/queue.py`, `access.py`,
`network.py`. `jobs/child.py` pasa al worker.

## 4. Workers

- Conexión saliente al servidor: funciona tras NAT y por Tailscale.
- Aislamiento por tarea: Job Objects en Windows y cgroups o systemd en Linux.
- Concurrencia por **VRAM** con costes medidos por el banco (separador ≈ 3 GB, alineador ≈ 2,1 GB):
  en 4 GB, una tarea de GPU. Si el reproductor está en el mismo PC, el worker le reserva VRAM y el
  decodificador, y baja de prioridad mientras suena una canción.
- Manifiesto de modelos con versión y hash; el servidor puede exigir una versión mínima.
- Telemetría (`nvidia-ml-py`): GPU, VRAM, temperatura, CPU, RAM, tarea y rendimiento.
- `fetch` (yt-dlp, `jobs/download.py`) solo en workers con capacidad `internet`.

## 5. Contenido: pistas independientes

| Pista | Contenido |
|---|---|
| `vocals` | Voz, Opus en Ogg (48 kHz) |
| `instrumental` | Música, Opus en Ogg (48 kHz) |
| `video` | Sin audio; varias versiones (720p, 1080p); H.264 siempre, HEVC o AV1 si el reproductor los decodifica por hardware |
| `lyrics` | Líneas, palabras y sílabas con tiempos y confianza (derivado de `Line/Word/Part`), sin rutas |

- Eje temporal único: t = 0 común; cada pista declara `offset`, `duración` y el pre-skip de Opus.
- La sonoridad (`loudness_lufs`) se guarda como metadato y la ganancia la aplica el reproductor; la
  pista no se toca. Hay que cambiar `karaoke_engine.audio.package_audio` (hoy saca m4a/AAC).
- Subtítulos como datos estructurados, dibujados por el reproductor. El ASS es solo exportación.
- Entrada y salida de reproducción no destructivas, en el elemento de la lista.
- Cada corrección crea una versión nueva del manifiesto; solo se re-descarga lo que cambia.
- Contratos en Pydantic → JSON Schema → tipos TS y Rust (`typify`). Los esquemas son la fuente.

## 6. Reproductor

> **Sustituido en parte por `decisiones/011`**: el audio (reloj, salidas, enrutado, tono,
> calibración de audio) sigue como aquí, en `kp-audio` en el backend. Las pantallas, el vídeo y la
> letra pasan a la web, y la calibración de pantalla, a la configuración de cada pantalla.

### Tecnología
Rust, con pipeline propio (`decisiones/001`): `cpal` (WASAPI y CoreAudio), Opus, ffmpeg con
decodificación por hardware (D3D11VA/NVDEC y VideoToolbox), y wgpu y winit con varias ventanas. Proceso sin interfaz propia, con un panel de diagnóstico.

### Sincronización
- **Reloj maestro**: el reloj hardware de la salida de audio principal.
- Segunda salida: remuestreo adaptativo (`rubato`) enganchado al maestro.
- **Vídeo**: se decodifica una sola vez, y cada pantalla presenta según el reloj maestro y su
  propio vsync (los refrescos pueden ser distintos).
- **Subtítulos**: se evalúan con el reloj maestro en cada fotograma de cada pantalla. El layout se
  porta a Rust y pasa los mismos casos compartidos que las versiones de Python y TS. El texto se
  dibuja con `cosmic-text`/`glyphon` y las fuentes OFL de los temas.
- **Tono**: signalsmith-stretch (MIT) por FFI, antes del enrutado. Su latencia se compensa en todas
  las pistas y en el ancla de posición.
- Hilos de audio y de render en tiempo real: sin asignaciones de memoria ni E/S bloqueante.
- **Calibración por salida** (latencia de audio y de pantalla), guardada por el ID estable del
  dispositivo.
- Objetivos: audio↔audio < 5 ms y A/V dentro de un fotograma, en salidas por cable o HDMI. El
  Bluetooth es «mejor esfuerzo», con calibración estática.

### Salidas y enrutado
- Detecta monitores y dispositivos de audio con ID estable, y vigila las altas y bajas en caliente.
- **Política de desconexión** por salida: si cae la salida maestra, pausa y avisa; si cae la
  secundaria o una pantalla, sigue y avisa. Configurable.
- **Matriz de enrutado** desde el control: pista → salida, con ganancia y retardo.
- Composición propia en cada pantalla (vídeo y letra, o solo letra con otro layout).
- **Pantalla de espera** entre canciones: siguiente canción, cuenta atrás y estado de descarga.

### Contenidos y órdenes
- Vinculado a una lista de producción; descarga en segundo plano (la siguiente canción primero),
  verifica hashes y reporta `ausente → descargando → verificando → listo`.
- Solo reproduce contenido cacheado y verificado.
- Las órdenes llevan marca temporal; la posición es un ancla `(posición, instante, velocidad)`.
- Si cae el servidor, sigue lo programado y reconcilia al volver.

## 7. Interfaz de control

Usuario: **un operador con teclado** (portátil o PC), como un técnico de cabina. Profesional,
rápida y flexible; todo se puede hacer sin ratón.

### Teclado
- **Paleta de comandos** `Ctrl/Cmd+K`: búsqueda difusa sobre acciones y entidades (canciones, listas,
  workers, salidas). Muestra el atajo de cada acción.
- **Atajos directos** (fuera de campos de texto): `Espacio` reproducir o pausar, `N`/`P` siguiente y
  anterior, `←/→` ±5 s, `+/-` volumen, `[`/`]` tono, `j/k` moverse, `Enter` abrir, `Alt+↑/↓` reordenar,
  `Supr` quitar (con deshacer), `/` buscar, `g` + letra para cambiar de sección (`g b` biblioteca,
  `g c` cola, `g w` workers, `g s` salidas), `?` chuleta.
- Selección múltiple (`Shift+j/k`, `x`) y acciones por lotes.
- Atajos reasignables y guardados por operador, con ámbitos por panel (no chocan con el editor).
- Deshacer y rehacer global (`Ctrl+Z`) en cola y listas, apoyado en el versionado optimista.
- Las acciones peligrosas se confirman con el teclado.

### Rapidez
- Respuesta visual < 100 ms; **UI optimista**, reconciliada por WebSocket y revertida con aviso si
  falla.
- Sin recargas ni sondeos; listas largas virtualizadas; búsqueda local instantánea.
- Sin el globo 3D en las vistas de operación.

### Flexibilidad
- **Paneles** redimensionables (cola · ahora suena · próximas · workers · salidas) con diseños
  guardados (preparación, directo); modo denso; claro y oscuro.
- Barra de estado fija: canción, tiempo restante, reproductor, salidas, GPU; avisos no intrusivos.
- Arrastrar archivos o pegar un enlace o una letra crea la tarea al momento.
- WCAG AA, foco siempre visible; gl, es y en.

### Funciones
- Subida reanudable de vídeo y audio; enlace de YouTube.
- Letras: `.txt`, editor y búsqueda en LRCLIB con candidatos (duración, si trae tiempos).
- Cola con etapa, progreso, ETA y worker; reintentar, cancelar, repriorizar.
- Workers: estado, GPU, VRAM, tarea y capacidades.
- Listas de producción y estado de cada contenido en el reproductor.
- Órdenes de transporte, entrada y salida, volumen y tono.
- Salidas y matriz de enrutado.
- Editor de letra y tiempos con mini reproductor web (`#lib/audio`, `SongClock`, `#lib/lyrics`).
- MP4 como tarea de worker.
- Varios controladores a la vez, con versionado optimista.

**Implementación**: un único registro de comandos en `web/src/lib/commands/` (id, título, ámbito,
atajo, `run()`) del que salen la paleta, los atajos, los menús y la chuleta. Los flujos principales
se prueban en e2e con Playwright **solo con teclado**.

## 8. Medición de sincronía

> Decidido: solo por software (`decisiones/002`). Lo que sigue queda como referencia.

Hoy no hay instrumentación, y por software no se ve la latencia del DAC, del HDMI ni del monitor.
Propuesta (≈ 40–60 €): una interfaz USB de 2 entradas (audio↔audio por correlación cruzada) y un
fotodiodo en la entrada de línea (A/V con destellos). Alternativa: un móvil a 240 fps (A/V ±4 ms).
Mientras tanto, marcas internas: el reloj hardware frente a la presentación de los fotogramas (DXGI
frame statistics en Windows, presentation-time en Wayland).

## 9. Fases

| Fase | Entrega | Criterio de salida |
|---|---|---|
| 0a | Spike del reproductor: GStreamer frente a propio, con 2 ventanas y 2 salidas | Decisión en `decisiones/001` |
| 0b | Banco de sincronía (§8) | Medida repetible de audio↔audio y A/V |
| 1 | Contratos v2, tipos Rust y TS, migrador v3 → manifiesto | Esquemas validados; demo `cloplas-laverca` convertida |
| 2 | Servidor: CAS, cola con lease, enrolado y TLS, API/WS, nativo en Windows | Tareas simuladas atraviesan la cola |
| 3 | Worker en Windows y Linux, tarea `make` gruesa | Canción completa en los dos SO; reasignación si uno cae |
| 3.5 | Corte vertical: reproductor mínimo (1 pantalla, 1 salida, sin tono) | Una canción de punta a punta en el equipo real |
| 4 | Control: comandos, paleta, atajos, paneles, subida, YouTube, letras, cola, workers, listas | Una canción de principio a fin solo con teclado; < 100 ms |
| 5 | Reproductor con 1 pantalla y 1 salida completo: aprovisionamiento, órdenes, pantalla de espera, tono | Objetivos de sincronía en el banco |
| 6 | 2 pantallas, 2.ª salida, enrutado, calibración, desconexión en caliente | Objetivos con ambas salidas |
| 7 | Editor con mini reproductor y MP4 | Paridad con v3 |
| 8 (opcional) | Varios reproductores sincronizados | Solo si surge la necesidad |

Los riesgos principales están en las fases 0, 5 y 6. `make ci` debe pasar en todas las fases, y la
calidad del motor no puede bajar de la de v3 (jamendo ≥ 99 % a ≤ 0,3 s).

## 10. Qué se reutiliza de v3

| Se reutiliza | Se reescribe | Se elimina |
|---|---|---|
| Motor (`make.py`, align, separación, transcripción, `video/`) | Cola, API y almacenamiento del servidor | PWA (`service-worker`, `lib/offline`) |
| Layout de subtítulos y sus casos (referencia para Rust) | Contratos (`karaoke.json` → manifiesto + pistas) | Fiesta (`parties.py`, `lib/party`, `lib/tv`) |
| Banco y modelos | Aislamiento de procesos (Windows) | Zonas de red y pasos de WSL |
| Editor, `#lib/audio`, `#lib/lyrics`, `jobs/{intake,progress,download}.py` | Empaquetado de audio (m4a → Opus) | |

## 11. Preguntas abiertas

Ver `ESTADO.md`.
