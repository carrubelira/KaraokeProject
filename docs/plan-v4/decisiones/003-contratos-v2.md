# 003 · Contratos v2: manifiesto, pistas por hash, nodos y órdenes

- **Fecha**: 19/11/2026
- **Estado**: aceptada
- **Afecta a**: todas las piezas

## Contexto

En v3, una canción es una carpeta con `karaoke.json` y archivos referenciados por ruta. En v4 los
reproductores y los workers descargan contenido de un servidor y tienen que saber, sin volver a
bajar nada, qué cambió entre dos versiones.

## Decisión

- **`packages/contracts`** gana `manifest.py`, `nodes.py`, `control.py` y `cas.py`. Los modelos
  v2 son estrictos (`extra="forbid"`): no hay lectores antiguos que contentar. Las líneas, palabras
  y sílabas se reutilizan de v1 tal cual, extras incluidos.
- **Manifiesto** (`schema_version` 2.x): `content_id` estable, `version` y `parent` (el hash de la
  versión anterior) y pistas `vocals`, `instrumental`, `video` (varias), `lyrics` y `cover`, cada
  una con su blob SHA-256, `offset` y `duration`. Se guarda en JSON canónico (claves ordenadas,
  sin espacios), así que su hash es su identidad.
- **Audio**: Opus en Ogg a 48 kHz, sin nivelar al codificar. `gain_db` es la ganancia que lleva la
  mezcla a −14 LUFS sin pasar −1 dBTP, la misma para las dos pistas; la aplica el reproductor (y
  el MP4). `karaoke.json` pasa a 1.3.0 con `audio.gain_db`; los paquetes anteriores (AAC ya
  nivelado) migran con ganancia 0.
- **Vídeo**: sin sonido, en H.264, HEVC o AV1 (otros códecs se recodifican a H.264).
  `Manifest.video_for` elige el más pequeño que cubre la pantalla entre los que el equipo decodifica.
- **`karaoke package <carpeta> --store <cas>`** guarda las pistas y el manifiesto, y sirve también
  de migrador de v3. `with_lyrics` crea la versión siguiente tras una edición: solo es nuevo el
  blob de la letra.
- **Tipos**: los esquemas se exportan con `make contracts`; TS con `json-schema-to-typescript`
  (`web/scripts/gen-contracts.mjs`, para todos los esquemas); en Rust, `kp-proto` está escrito a
  mano. Se prefirió a `typify` porque así los tipos de Rust son legibles y los enums son
  idiomáticos. Lo mantiene honrado `fixtures/contracts-v2/`: cada ejemplo valida en Python y en
  Rust debe volver idéntico.

## Consecuencias

- Toda la reproducción v4 lee manifiestos; `karaoke.json` queda como formato de trabajo del motor
  y del editor hasta la fase 7.
- Un cambio de contrato toca tres sitios (pydantic, esquema regenerado y `kp-proto`), y las
  pruebas con los ejemplos fallan si alguno se queda atrás.
