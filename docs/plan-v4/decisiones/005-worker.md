# 005 · Worker v4: pull, un hueco de GPU y aislamiento por SO

- **Fecha**: 19/11/2026
- **Estado**: aceptada
- **Afecta a**: worker, servidor

## Decisión

- Paquete `karaoke-worker`. Reutiliza el `runner`, el lanzador de procesos hijo (`child`) y la
  descarga con yt-dlp de v3, que se mueven del servidor aquí.
- **Bucle** (`agent.Agent`): latido cada pocos segundos con telemetría NVML; pide un *lease* con
  la VRAM libre (0 si su hueco de GPU está ocupado, de modo que solo recibe descargas). Hace una
  tarea de GPU y hasta dos de CPU a la vez. Toda llamada al servidor va en un hilo, así una subida
  larga no para el latido.
- **Tareas**: `fetch` sube la canción como blob; `make` ejecuta el motor en un proceso hijo,
  convierte el paquete en manifiesto (`karaoke_engine.package.build_manifest`) y sube solo los
  blobs que el servidor no tiene; `render` reconstruye la carpeta desde el manifiesto
  (`package.unpack`) y exporta el MP4.
- **Aislamiento**: un *scope* de systemd con `MemoryMax` en Linux; en Windows un Job Object con
  límite de memoria y `KILL_ON_JOB_CLOSE`, que además mata al hijo si muere el worker.
- **TLS**: al enrolarse descarga el certificado, comprueba su huella contra la que el operador
  copia del servidor (o confía en el primer uso, con aviso) y desde entonces solo acepta ese.
- **Mismo equipo**: con `--same-host` lee los blobs del disco del servidor. Con `--player-lock`
  no empieza trabajo de GPU mientras el reproductor de ese equipo toque el archivo.

## Consecuencias

- Las pruebas recorren el ciclo completo contra la app real del servidor con el motor de mentira:
  hacer, exportar, cancelar y fallar.
- La CI de Windows ejecuta los tests del worker sin GPU (`.github/workflows/player.yml`).
