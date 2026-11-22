# 011 · Pantallas web sincronizadas y audio en el backend

- **Fecha**: 22/11/2026
- **Estado**: aceptada; hecha salvo la prueba en la Pi (11.0) y el kiosco (11.7)
- **Afecta a**: reproductor, servidor, worker, contratos, web, CI
- **Sustituye**: en `00-vision.md`, «reproductor nativo, sin navegador», «TLS siempre», «se
  descarta el reproductor web» y el §6 de pantallas; las pantallas de `001` y `006`; «una cola por
  pantalla» de `010`.

## Contexto

Hoy `kp-player` lo hace todo en una sola máquina: la caché, el audio (`cpal` con un `Follower` por
salida), el tono, el vídeo (FFmpeg y wgpu) y la letra (`kp-layout`, la tercera copia de la
maquetación). El usuario quiere:

- **un reproductor por backend**;
- **el audio en el backend**: cada pista va a las tarjetas de sonido o DAC conectados a él;
- **pantallas web** conectadas al backend en todo momento, que muestran todas lo mismo (vídeo y
  letra) y en sincronía. Corren en navegadores de Windows, Linux y macOS, y en kioscos Tauri sobre
  **Raspberry Pi**;
- **pantallas como máquina de estados**: `idle`, `provisioning`, `syncing`, `waiting`, `playing`,
  `pause` y `error`, ampliable;
- que **el backend marque el ritmo**, con medidas proactivas contra las esperas;
- todo en **la misma LAN**, nunca entre redes.

Lo que eligió en la revisión:

| Tema | Elección |
|---|---|
| Motor de audio | *Sidecar* en Rust (`kp-audio`), supervisado por el servidor |
| Arranque | **Siempre lo da el operador.** La consola muestra quién está listo; si falta una pantalla, empezar pide confirmación y la rezagada se incorpora en marcha. El audio tiene que estar listo |
| Red | **HTTP plano en todo el servidor** (sin TLS) |
| Pantallas | **Abiertas en la LAN**: cualquier navegador que abra `/pantalla` es una pantalla |
| Vídeo | `<video>` mudo con servo de `playbackRate`; WebCodecs queda como mejora |
| Kiosco | Raspberry Pi |

## Decisión

### Piezas

```
 Consola ─HTTP/WS─► SERVIDOR ── sesión (máquina de estados), ancla, reloj, cola única
                      │  WS local                  │  WS: time, session, config
                      ▼                            ▼
                kp-audio (Rust)             Pantallas web × N (navegador / Tauri en Pi)
                DAC 1, DAC 2, tono          vídeo mudo + letra; sin sonido
```

- **`kp-audio`** es lo que queda de `kp-player` sin pantallas: `kp-clock`, `kp-mix`, `audio.rs`
  y `pitch.rs`, leyendo los blobs en el almacén del servidor (`--store`; ya no hace falta
  `kp-cache`). El servidor lo lanza, lo vuelve a lanzar si muere y le habla por un WebSocket en
  `127.0.0.1` con un secreto de cada arranque. El Opus se decodifica con **libopus** (crates `ogg`
  y `opus`; libopus se compila con cmake si el sistema no la tiene): FFmpeg sale del build y la
  máquina del servidor no necesita `ffmpeg` para sonar. Comprobado frente a `ffmpeg` con pistas
  reales del motor: la misma longitud y la misma energía con seis cifras. bindgen y libclang siguen
  haciendo falta para Signalsmith Stretch (el tono).
- **Pantalla**: la ruta `/pantalla` de la misma SPA, una entrada ligera sin el armazón de la
  consola. Reutiliza `lib/lyrics` (`Lyrics.svelte` ya dibuja a partir de un `PlaybackClock`).
- **Servidor**: el `PlayerHub` multirreproductor pasa a ser un **`Stage`** único. Lleva la sesión,
  el registro de pantallas, el enlace con `kp-audio` y la cola única.

### El tiempo

- **La línea de tiempo del servidor es la verdad.** `now_us()` usaba `time.time_ns()`, el reloj
  de pared, que NTP corrige a saltos o a tirones. Pasa a `time.perf_counter_ns()`: monótono y fino
  (QueryPerformanceCounter en Windows). Medido: en Windows, el `time.monotonic` de Python 3.12
  avanza a saltos de 15,6 ms y las pantallas le medían 350 ppm de deriva frente a su propio reloj;
  con `perf_counter` la deriva medida es de 0 a 4 ppm. El reloj de pared queda para mostrar y para
  los logs.
- **Audio**: cada salida de `kp-audio` suena en el instante que marca el ancla, con su latencia
  compensada (el `Follower` y la calibración por salida de hoy). No se envía la posición del audio a
  las pantallas: el audio ya va enganchado a la línea de tiempo con menos de 1 ms de error.
- **Pantallas**: port a TS de `kp_core::ServerClock`.
  - Al conectar lanza una ráfaga de 8 pings; después, uno cada 2 s.
  - Se queda con la muestra de menor ida y vuelta de una ventana de 30 s, y estima la deriva por
    mínimos cuadrados.
  - Las correcciones se aplican poco a poco, sin saltos.
- **Cada fotograma se calcula para cuándo se verá**:
  - letra: la marca de `requestAnimationFrame` + un refresco + `display_ms` de la pantalla;
  - vídeo: `expectedDisplayTime` de `requestVideoFrameCallback` + `display_ms`.

### Máquina de estados de la sesión (servidor)

| Estado | Qué significa | Sale a |
|---|---|---|
| `idle` | nada en el aire | `cueing` (el operador elige canción o la cola avanza) |
| `cueing` | `epoch` nuevo; audio y pantallas preparan el elemento y la posición | `cued` cuando `kp-audio` está listo |
| `cued` | el audio está listo; la consola muestra qué pantallas lo están y qué falta | `playing` **solo por orden del operador** (pide confirmación si falta alguna pantalla) |
| `playing` | ancla con velocidad 1 | `paused`, `cueing` (otra canción), `ended` |
| `paused` | ancla con velocidad 0; todos quietos en el mismo fotograma | `playing` (orden del operador), `cueing` |
| `ended` | llegó al final o al punto de salida | `cueing` de la siguiente, que se queda en `cued` |
| `fault` | `kp-audio` no arranca o no hay salida maestra | `cueing` cuando se recupera |

Un salto (`seek`) no cambia el estado. Si la sesión está sonando, el ancla nueva va 400 ms en el
futuro, y las pantallas buscan ese punto por adelantado.

### Máquina de estados de la pantalla (web)

Es un reductor puro, `transition(estado, evento) → {estado, efectos}`, sin dependencias y probado
con vitest. Un intérprete aparte ejecuta los efectos: descargar, buscar en el vídeo, enviar
`ready`. Los nombres de los estados van en los contratos, así que la consola y el servidor hablan
el mismo vocabulario.

| Estado | Entra cuando | Sale a |
|---|---|---|
| `connecting` *(nuevo)* | arranca, o pierde el enlace sin nada en curso | según la sesión recibida |
| `idle` | la sesión no tiene canción | `provisioning` o `syncing` |
| `provisioning` | el elemento pedido no está entero y verificado; informa del progreso | `syncing`; `error` solo si no se puede (códec no soportado, sin espacio) |
| `syncing` | busca el fotograma de la posición, espera a verlo presentado y maqueta la letra | `waiting` (o `playing`, si llega con la sesión ya en marcha) |
| `waiting` | primer fotograma en pantalla y letra lista; manda `ready(epoch)` | `playing` en el instante del ancla |
| `playing` | sigue el ancla | `pause`, `syncing` (desvío grande o salto), `idle` |
| `pause` | ancla con velocidad 0 | `playing`, `syncing` (salto) |
| `error` | irrecuperable | solo recargando |

**Indicadores, no estados** (se informan junto al estado):

- `offline`: si se cae el enlace en mitad de una canción, la pantalla sigue con la última ancla y,
  al volver, se pone al día con la foto de la sesión;
- `hidden`: la pestaña no se ve y el navegador deja de dibujar;
- `degraded`: no consigue seguir el vídeo y solo dibuja la letra;
- la precarga de las canciones siguientes.

### Protocolo

El servidor publica **la sesión como estado declarativo con versión**, no órdenes sueltas. Cada
pantalla y `kp-audio` se ponen al día con la última versión que reciben. Así, conectarse a mitad de
canción, reconectarse y arrancar siguen el mismo camino, y los mensajes viejos se descartan por
`version` y `epoch`.

- **Del servidor a la pantalla**:
  - `time{now, sent}`;
  - `session{version, epoch, state, item, manifest, anchor, upcoming[K]}`;
  - `config{layout, theme, display_ms, video_max_height}`.
- **De la pantalla al servidor**:
  - `time-request{sent}`;
  - `status{epoch, state, flags, cache[], ready, sync{error_ms_p95, rtt_ms, dropped}}`, cada
    segundo y en cada cambio.
- **Márgenes de los anclas**: 120 ms para empezar o pausar (ajustado al RTT p99 medido) y 400 ms
  para un salto mientras suena. Hoy son 300 ms fijos. Bastan márgenes cortos porque cuando el
  operador da la orden todos están ya preparados.

### Vídeo en la pantalla

- `<video muted playsinline>` con el blob local.
- Error `e = mediaTime − objetivo`:
  - |e| < 15 ms: velocidad 1;
  - entre 15 y 150 ms: `playbackRate = 1 − k·e`, limitado a ±3 %;
  - más de 150 ms: salta al objetivo más lo que tardó el último salto, sin estados intermedios.
- Si no hay `requestVideoFrameCallback`, se muestrea `currentTime` en cada `requestAnimationFrame`
  y se filtra (peor precisión, pero funciona).
- **Doble búfer**: mientras suena la canción N, la N+1 espera en un segundo `<video>`, parado en su
  primer fotograma, con su letra maquetada y sus fuentes cargadas. Pasar de una a otra es
  intercambiar elementos.

### Contenido en la pantalla

- Se descargan del CAS por HTTP con `Range`, **en orden**: lo que está en el aire, la siguiente y
  luego las K siguientes. K es 3 en un portátil y 2 en una Pi.
- Se guardan en IndexedDB por SHA-256 (OPFS y la Cache API necesitan HTTPS). El hash se comprueba
  en un Web Worker con un SHA-256 en wasm (`hash-wasm`), porque sin HTTPS no hay `crypto.subtle`.
- Se borra lo que ya no está en la cola, empezando por lo más antiguo.
- Cada pantalla declara sus códecs (`canPlayType`) y la altura máxima que admite, y
  `Manifest.video_for` elige la versión.

### Red y acceso

- **HTTP en todo el servidor.** Desaparecen `tls.py`, la huella fijada al enrolar, `--no-tls` y
  `--name`. Workers y operadores conservan su token, que ahora viaja en claro por la LAN (aceptado).
- **Pantallas abiertas.** Cada navegador inventa un `screen_id` estable y lo guarda en
  `localStorage`. Si hay varias ventanas, se distinguen con `?screen=`. El servidor guarda por
  `screen_id` el nombre, el layout, el tema y la calibración que pone el operador. Una pantalla
  nunca bloquea el arranque, así que una desconocida no estorba.
- **Monitor de la consola**: es una pantalla en modo `preview`. Usa el mismo código, pero no cuenta
  para saber quién está listo.
- **Pantalla completa** en un portátil: un aviso de «pulsa para pantalla completa», porque el
  navegador exige un gesto. Sin HTTPS no hay Wake Lock: lo resuelven el kiosco y el sistema.

### Kiosco en Raspberry Pi

- Tauri como envoltorio fino:
  - una ventana a pantalla completa por monitor, que carga
    `http://BACKEND:8765/pantalla?screen=<equipo>-<monitor>`, así que la versión siempre es la del
    backend y el kiosco no hay que actualizarlo;
  - busca el backend por mDNS (`_karaoke._tcp`);
  - arranca con systemd, oculta el cursor y no deja que la pantalla se apague.
- **Riesgo principal**:
  - la Pi 5 no decodifica H.264 por hardware: solo tiene HEVC, por V4L2 sin estado;
  - Tauri en Linux usa WebKitGTK + GStreamer, con regresiones de rendimiento conocidas en la Pi 5;
  - WebKitGTK sí soporta `requestVideoFrameCallback` (bug WebKit 233541, resuelto).
- **Plan para la Pi**:
  - vídeo H.264 a 720p decodificado por software, una versión que el worker genera siempre;
  - HEVC por hardware solo si la prueba demuestra que WebKitGTK usa `v4l2slh265dec`.
- **Si WebKitGTK no da la talla, la alternativa es Chromium en modo kiosco** en la Pi, con el mismo
  código web.

## Qué se elimina, se simplifica y se reutiliza

| Se elimina | Se simplifica | Se reutiliza |
|---|---|---|
| `player/.../screens.rs`, `video.rs` y el vídeo de `program.rs` | `PlayerHub` multirreproductor → `Stage` único | `kp-clock`, `kp-mix`, `audio.rs`, `pitch.rs` |
| El crate `kp-layout` y sus casos en Rust (la maquetación queda en Python para el MP4 y en TS para las pantallas) | Las colas por `player_id` → una cola; el selector de reproductor de la consola | `kp-cache`, en local |
| `kp-media` (FFmpeg); wgpu, winit, glyphon y pollster | `queue_on` del alta → «a la cola» | `kp_core::Timeline`, y `ServerClock` portado a TS |
| Los escenarios de pantalla de `kp-syncbench` (pasan a un banco en TS) | `PlayerStatus` → estado de `kp-audio` + estado por pantalla | `Lyrics.svelte`, `lib/lyrics` y sus casos compartidos |
| `Routing.screens` y `Calibration.display_ms` (pasan a la configuración de cada pantalla) | El enrolado de reproductores (ahora es un proceso local del servidor) | CAS con `Range`, versiones del manifiesto |
| TLS: `tls.py`, huella, `kp-net` con certificado fijado, `--fingerprint` del worker | `player.yml` en CI: Rust sin FFmpeg | El editor y su `lib/audio` |
| `--player-lock` del worker (el servidor sabe cuándo suena) | | |

## Fases

| Fase | Entrega | Criterio de salida |
|---|---|---|
| 11.0 | Prueba en la Pi 5 (y la 4): Tauri/WebKitGTK frente a Chromium en kiosco; H.264 a 720p y 1080p, HEVC, `requestVideoFrameCallback`, letra | Una canción entera a 720p con menos del 1 % de fotogramas perdidos y la letra a 60 fps; se elige el navegador y la escalera de códecs |
| 11.1 | Contratos: sesión, estados, mensajes, configuración de pantalla; `kp-proto`; ejemplos | Esquemas validados en Python, TS y Rust |
| 11.2 | `kp-audio`: quitar pantallas y FFmpeg (libopus), `ready` por `epoch`, supervisado por el servidor | `make e2e` con dos salidas simuladas y orden del operador |
| 11.3 | Servidor: `Stage`, reloj monótono, pantallas abiertas, quién está listo, cola única, sin TLS | Pruebas de la máquina de la sesión, reconexión y entrada a mitad de canción |
| 11.4 | Pantalla web: reloj, reductor, contenido en IndexedDB, servo de vídeo, doble búfer, pantalla de espera | Banco en TS (jitter de red y deriva simulados): pantalla ↔ línea de tiempo < 1 fotograma |
| 11.5 | Consola: panel de pantallas (estado, quién está listo, salud, layout, calibración), empezar con aviso, previsión «la siguiente no estará lista a tiempo» | e2e solo con teclado |
| 11.6 | e2e: dos navegadores de Playwright + `kp-audio` simulado | Error entre pantallas p95 < 1 fotograma |
| 11.7 | Kiosco Tauri para la Pi: mDNS, pantalla completa por monitor, arranque automático | Arranca sin teclado y se recupera si se reinicia el backend |
| 11.8 | Limpieza y documentación (`player.md` → `kp-audio.md`, `screens.md`, `architecture.md`) | `make ci` |

## Riesgos

- **La Pi 5** (ver más arriba): se mide antes que nada, en la fase 11.0.
- **Wi-Fi con ahorro de energía**: el jitter puede pasar de 50 ms. El filtro de menor RTT lo
  absorbe, pero en los kioscos se recomienda cable.
- **El navegador de un portátil**: una pestaña oculta deja de dibujar (se informa con `hidden` y
  se resincroniza al volver), y la pantalla completa necesita un gesto.
- **Lo que el software no ve** (el retardo de la tele, del DAC): calibración por salida de audio y
  por pantalla.

## Lo que se midió al hacerlo

- `make e2e-v4` en Windows: la canción preparada no suena hasta la orden del operador; después,
  las dos salidas virtuales suenan a la vez (la segunda absorbe +63 ppm) y el sonido está a
  0,000004 ms de la línea de tiempo.
- Banco en TS (`web/src/lib/screen/sync.test.ts`): por cable, el fotograma mostrado contiene
  siempre el audio que suena y la letra está a menos de 1 ms; con una Wi-Fi hostil (jitter de 6 ms
  y un 15 % de picos de 60 ms), 0,7 ms fuera del fotograma y 2,2 ms en la letra (p95).
- Dos pantallas de Edge en el mismo portátil, contra el servidor real y `kp-audio`: 1 ms entre
  ellas y unos 10 ms frente a la línea de tiempo, estables toda la canción (un tercio de fotograma
  a 30 fps). El e2e de Playwright con dos navegadores pasa: descargan, esperan en el primer
  fotograma, el servidor no deja empezar sin el operador, y suenan y pausan a la vez.
- Fallos encontrados por el camino y corregidos: dos búsquedas a la vez en el mismo `<video>` se
  pisaban el `onseeked` (la misma canción dos veces en la cola); Chromium olvida las
  `requestVideoFrameCallback` al cambiar de fuente; y una página que no dibuja (oculta) no
  empezaba nunca, así que el arranque y la pausa van también por un temporizador puesto al instante
  del ancla.

## Consecuencias

- Las tres copias de la maquetación se quedan en dos, y el reproductor se compila sin FFmpeg.
- La sincronía entre pantallas pasa a ser un requisito (antes era la fase 8 opcional). Se mide con
  un banco en TS y con el e2e de dos navegadores.
- `00-vision.md` §1, §2 y §6 y `ESTADO.md` se actualizan en el mismo PR.
