# Plan v4 · Estado

Tablero por fases (`00-vision.md` §9). Cada fase actualiza **su fila** tras cada hito.

| Fase | Entrega | Estado | Rama | Último hito |
|---|---|---|---|---|
| 0a | Spike del reproductor (GStreamer frente a propio; libmpv como referencia) | pendiente | — | — |
| 0b | Banco de medición de sincronía | bloqueada: falta el hardware de medida (§8) | — | — |
| 1 | Contratos v2 y migrador v3 → manifiesto | pendiente | — | — |
| 2 | Servidor: CAS, cola con lease, enrolado y TLS, API/WS | pendiente | — | — |
| 3 | Worker en Windows y Linux, tarea `make` gruesa | pendiente | — | — |
| 3.5 | Corte vertical: reproductor mínimo | pendiente | — | — |
| 4 | Control: comandos, paleta, atajos, paneles, cola | pendiente | — | — |
| 5 | Reproductor: 1 pantalla y 1 salida completas, con tono | pendiente | — | — |
| 6 | Reproductor: 2 pantallas, 2.ª salida, enrutado, calibración | pendiente | — | — |
| 7 | Editor con mini reproductor y MP4 | pendiente | — | — |
| 8 | (opcional) Varios reproductores | fuera hasta que haga falta | — | — |

## Preguntas abiertas

- Hardware de medida: comprar una interfaz USB de 2 entradas y un fotodiodo (propuesto) o medir
  solo por software más un móvil a 240 fps.
- Equipo del reproductor: GPU, SO, monitores y, en Linux, si es Wayland o X11.
- Tono sobre la voz guía: transportar ambas pistas (propuesto) o silenciar la voz.
- Globo 3D de «Noite»: solo en la pantalla de inicio o eliminarlo de la interfaz de control.
