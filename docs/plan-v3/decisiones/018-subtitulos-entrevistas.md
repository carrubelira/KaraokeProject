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

## Cómo se midió

No hay entrevistas gallegas públicas con subtítulos cronometrados, así que el banco las fabrica
(`karaoke-bench fetch-speech`, `bench/sets/speech-gl.toml`): 12 diálogos de unos 5 minutos con
frases leídas de OpenSLR 77 (CC BY-SA 4.0), un «entrevistador» que pregunta corto y un
«entrevistado» que responde largo, la mitad con dos voces del mismo sexo. La referencia es el
texto, quién dice cada frase y dónde empieza y acaba su voz. Es habla leída y limpia: sirve para
comparar modelos y ajustes; cómo se leen las entrevistas reales se juzga viéndolas.

| Pipeline (`bench/pipelines/`) | Palabras mal (WER) | Entrada del subtítulo: error (mediana · 90 %) | Sesgo | Tiempo por hora |
|---|---|---|---|---|
| `captions-hitz` (HiTZ, haz 5) | 7,46 % | 0,408 · 0,859 s | 0,39 s antes | 6,0 min |
| `captions-hitz-b1` (HiTZ, haz 1) | 7,30 % | 0,389 · 0,809 s | 0,38 s antes | 5,4 min |
| `captions-nos` (Nós turbo, haz 5) | 8,28 % | 0,458 · 0,829 s | 0,46 s antes | 2,6 min |
| `captions-nos-b1` (Nós turbo, haz 1) | 7,60 % | 0,457 · 0,829 s | 0,45 s antes | 2,4 min |
| `captions-turbo` (large-v3-turbo, haz 5) | 15,16 % | 0,336 · 0,864 s | 0,33 s antes | 2,8 min |
| `captions-refine-b1` (HiTZ, haz 1, tiempos del alineador) | 7,30 % | **0,051 · 0,339 s** | 0,04 s después | 7,5 min |
| **`captions-default`** (lo anterior y quién habla) | 7,30 % | **0,050 · 0,257 s** | 0,05 s después | 8,7 min |

(El tiempo incluye cargar el modelo en cada diálogo; con una entrevista larga pesa menos.)

- **Modelo: HiTZ.** Con la semilla fijada, HiTZ y Nós turbo con haz 1 quedan a 0,3 puntos (7,30
  y 7,60 %), y Nós va en menos de la mitad de tiempo. La regla del plan (empate de ±1 punto, gana
  el rápido) daría Nós, pero se queda HiTZ: con habla real y difícil (las canciones gallegas de la
  decisión 005) le sacó 10 puntos a Nós, las entrevistas en castrapo se parecen más a eso que a
  frases leídas, y la velocidad ya sobra (10 min por hora frente a la meta de 20). `--model
  nos-turbo-gl` lo cambia. Antes de fijar la semilla, la misma prueba variaba un punto de una
  vez a otra (Whisper vuelve a muestrear con temperatura donde duda).
- **Haz 1**: el mismo error que 5 en la mitad de tiempo.
- **Tiempos de palabra**: los de Whisper entran antes de la voz (de 0,76 a 0,07 s). El alineador
  CTC gallego del karaoke, por tramos entre pausas, los deja a 0,05 s.
- **Quién habla**: con huellas de WeSpeaker, 0,0 % de palabras con el hablante cambiado en los 12
  diálogos (con los ajustes por defecto también). Un primer modelo wav2vec2 (Apache-2.0) fallaba en el 20–37 % de las ventanas con dos
  voces del mismo sexo, y el de WavLM es CC BY-SA, que el proyecto no admite.
- **Normas**: ningún subtítulo con más de dos líneas, líneas largas, solapes ni huecos de menos
  de dos fotogramas. Pasan de 17 caracteres por segundo el 22 % (156 de 698): el texto es literal
  y se queda en pantalla lo que deja el siguiente (antes de estirarlos hacia los huecos libres,
  el 32 %). Tres duran menos de 5/6 s porque no hay sitio antes del siguiente.

Probado también con las entrevistas reales del dueño (en local, nunca en el repo): seis vídeos
4K de una cámara, 2 h 50 min, en 29 min (unos 10 min por hora), con 3,3 GB de RAM como mucho en
un proceso y la huella SHA-256 de los vídeos idéntica antes y después. De ahí salen la transcripción por tramos (una hora de golpe pasaba
de 5 GB de RAM), la búsqueda de cortes en paralelo, las huellas por lotes y los ajustes de la
lista de revisión.

## Consecuencias

- El motor gana `karaoke_engine.captions` y la orden `karaoke captions`; `transcribe.py` expone
  `WhisperTranscriber.whisper_for_language` e `is_loop`.
- Las teles del museo aún no pintan un `.vtt` (su reproductor lo ignora): es la siguiente pieza,
  en su propio repositorio.
