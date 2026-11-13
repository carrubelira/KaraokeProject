# 018 · Subtítulos profesionales para entrevistas

- **Fecha**: 13/11/2026
- **Estado**: propuesta (rama `v3/subtitulos`); se aprueba con su PR
- **Afecta a**: motor (`karaoke_engine.captions`, `transcribe.py`, CLI `karaoke captions`), banco
  (conjunto de habla y métricas de subtítulos). No cambia contratos, API ni web.

## Contexto

El dueño colabora con una asociación cultural que monta un museo de cultura marinera. Tiene
entrevistas en gallego de más de una hora, en 4K y alta tasa (unos 57 Mbit/s), en un disco
externo, y quiere subtítulos «como los haría un profesional de la edición de vídeo»: frase a
frase, sincronizados con la voz, sin resaltado progresivo y **sin que el vídeo pierda nada de
calidad**. Los revisará en DaVinci Resolve y se verán en las teles del museo y en su archivo,
que ya espera un `.vtt` junto a cada entrevista.

La mayoría de quienes hablan usan un gallego coloquial con gheada y seseo; los subtítulos van en
ortografía normativa, con sus palabras. En las entrevistas se oyen el entrevistador y el
entrevistado.

## Decisión

- **Fichero aparte, nunca el vídeo.** Quemar los subtítulos o meterlos como pista obliga a
  escribir un vídeo nuevo: recodificar, o reescribir decenas de GB. Un profesional entrega un
  `.srt`/`.vtt` junto al vídeo siempre que el reproductor lo admite. `karaoke captions` deja al
  lado de cada vídeo `<nombre>.gl.srt`, `<nombre>.gl.vtt` y `<nombre>.gl.revisar.txt`; el vídeo
  solo se lee, una vez, y un test comprueba su huella, tamaño y fecha.
- **Normas de subtitulado** de las guías de Netflix (general y castellano) y la UNE 153010: dos
  líneas de 42 caracteres como mucho, lectura de 15 caracteres por segundo (aviso a partir de
  17), de 5/6 s a 7 s, dos fotogramas entre subtítulos, cortes de plano a 12 fotogramas, guion
  sin espacio cuando hablan dos. Los tiempos se calculan en fotogramas enteros.
- **Habla con tiempos por palabra**: Whisper con el modelo gallego, el detector de voz Silero en
  lugar del de voz cantada, y fuera las frases hechas que Whisper inventa en los silencios.
- **Revisión en DaVinci**: línea de tiempo nueva desde el fichero entregado empezando en
  `00:00:00:00`, exportar solo la pista y `--from-srt` para rehacer el `.vtt`, que se niega si
  los tiempos llegan desplazados una cantidad fija (la hora de DaVinci).

Guía técnica: [`docs/captions.md`](../../captions.md).

## Consecuencias

- El motor gana `karaoke_engine.captions` y la orden `karaoke captions`; `transcribe.py` expone
  `WhisperTranscriber.whisper_for_language` e `is_loop`.
- Las teles del museo aún no pintan un `.vtt` (su reproductor lo ignora): es la siguiente pieza,
  en su propio repositorio.
