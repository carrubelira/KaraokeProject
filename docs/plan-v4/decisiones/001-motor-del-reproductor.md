# 001 · Motor del reproductor: pipeline propio en Rust

- **Fecha**: 19/11/2026
- **Estado**: aceptada
- **Afecta a**: reproductor (fases 3.5, 5 y 6)

## Contexto

El reproductor va en Windows con NVIDIA o en macOS; Linux queda solo para desarrollo. Tiene que
llevar dos pantallas y una o dos salidas de audio con un solo reloj. No hay ninguno de esos
aparatos para un spike comparativo, así que la decisión se toma sobre lo que cada opción permite.

- **libmpv**: una instancia tiene un reloj y una salida de audio. Dos pantallas son dos instancias
  sin un reloj común, y no puede mandar pistas distintas a dos dispositivos. Se descarta.
- **GStreamer**: tiene reloj de pipeline común y varios *sinks*, pero exige instalar su runtime en
  Windows y macOS (más de 100 MB y plugins sueltos), y la composición de la letra iría igualmente
  en wgpu. Se descarta por el despliegue.
- **Propio**: más código, pero todo está bajo control y casi todo se prueba sin aparato.

## Decisión

Workspace `player/` en Rust.

- **Crates sin plataforma**, probados en la CI de Linux: `kp-clock` (reloj maestro, anclas,
  ritmo medido y control de deriva), `kp-mix` (pistas, matriz de enrutado, ganancia, retardo,
  tono y remuestreo), `kp-syncbench` (banco, decisión 002) y los que vengan (protocolo, caché,
  layout de la letra, planificador).
- **Capa nativa**: `cpal` (WASAPI y CoreAudio), Opus con `ogg` y libopus, vídeo con ffmpeg
  (D3D11VA/NVDEC y VideoToolbox), `wgpu` y `winit` con una ventana por pantalla, y
  signalsmith-stretch para el tono.
- **Remuestreo de la segunda salida**: interpolación cúbica de razón variable propia. La
  corrección es de cientos de ppm, inaudible, y así no hay que depender de la API de `rubato`.
- **Tono**: un `Pitcher` por pista y salida. El mezclador lee por delante tanto como la latencia
  del algoritmo, de modo que transportar no desplaza la canción. Se aplica a la voz y a la música.

## Consecuencias

- El reloj maestro es un *seqlock* sobre atómicos: el hilo de audio nunca se bloquea ni reserva
  memoria.
- La CI compila la capa nativa para Windows y macOS. La prueba en el aparato real se hace con
  `--diagnose`.
