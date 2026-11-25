# 004 · Servidor v4: almacén por contenido, cola con lease y nodos enrolados

- **Fecha**: 19/11/2026
- **Estado**: aceptada
- **Afecta a**: servidor, worker, reproductor, control

## Decisión

- **Reescrito** sobre el mismo FastAPI. Desaparecen las zonas de red, el emparejado de aparatos,
  la fiesta, la cola de un trabajo en proceso hijo y los pasos de WSL. Base de datos nueva
  (`karaoke-v4.db`); la de v3 no se toca.
- **CAS** en disco (`karaoke_contracts.cas.BlobStore`): `GET` con `Range` (las descargas se
  reanudan), `PUT` con el hash comprobado mientras llega, ruta local para los nodos del mismo
  equipo, recolección por referencias con una hora de gracia, papelera de 30 días y cuota.
- **Subidas reanudables** al estilo tus (`POST`, `HEAD`, `PATCH` con `Upload-Offset`).
- **Cola** (`queue.TaskQueue`): trabajos hechos de tareas en DAG (`fetch → make`, `make`,
  `render`). *Lease* renovado con latido y progreso; si vence, la tarea pasa a otro worker (tres
  intentos). Se asigna por prioridad y, a igualdad, por afinidad de datos: gana el worker que hizo
  las dependencias. Se filtra por tipo de tarea, internet, VRAM libre, worker fijado y «hay un
  reproductor sonando en ese equipo». Completar dos veces con el mismo *lease* no hace nada, y un
  *lease* caducado se rechaza (409). Se puede cancelar, pausar, reanudar, reintentar, cambiar la
  prioridad y fijar a un worker. El ETA sale de la media de las 20 últimas tareas de su tipo.
- **Nodos**: un token de un solo uso (`karaoke-server enroll` o la UI) se cambia por una
  credencial propia; se guardan solo hashes y se puede revocar. TLS siempre, con certificado
  ECDSA propio cuya huella fija el nodo al enrolarse.
- **Operadores**: token propio (`karaoke-server operator add`), en cookie HttpOnly o Bearer;
  guardan sus preferencias (atajos, paneles) en el servidor.
- **Listas** con versionado optimista: escribir sobre una versión vieja da 409 con la lista actual.
- **Reproductores**: socket propio; el servidor les envía la hora, la configuración, la lista y
  las órdenes. Las órdenes llevan un ancla 300 ms en el futuro con el reloj del servidor.
  `next`/`previous` resuelven el elemento en el servidor; volumen y tono se limitan a su rango.
- **Control**: `/api/events` manda una foto completa al conectar y luego cada cambio; una
  conexión que se queda atrás se cierra (reconecta y recarga).
- **Ediciones**: `PUT /api/contents/{id}/lyrics` crea la versión siguiente (solo es nuevo el blob
  de la letra) y se rechaza si la canción cambió mientras tanto.

## Consecuencias

- La web de v3 no tiene servidor hasta la fase 4; su e2e contra el servidor se reescribe allí.
