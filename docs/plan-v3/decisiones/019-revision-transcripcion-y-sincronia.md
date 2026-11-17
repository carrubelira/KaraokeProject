# 019 · Revisión de transcripción y sincronía con lo que hay en noviembre de 2026

- **Fecha**: 16/11/2026
- **Estado**: propuesta (rama `v3/subtitulos`); se aprueba con su PR
- **Afecta a**: C4 (`align/`, `transcribe.py`, `make.py`), C2 (banco: referencias por línea, WER
  tolerante), C8 (memoria y tiempo de un trabajo), C10 (`NOTICE.md`, idiomas y modelos)

## Contexto

Con el plan v3 cerrado, el dueño pidió repasar el área de transcripción y sincronización: comprobar
desde cero, con lo que existe hoy, si lo elegido en `005` (29/10) sigue siendo lo mejor posible, en
general y en gallego, y cambiar lo que haga falta.

Dónde estaba (`005`, `016`): con letra, JamendoLyrics 98,8 % de palabras a ≤ 0,3 s (media
0,093 s), gallego validado 99,8 %, y un 74–79 % en las dos canciones gallegas urbanas con
tiempos hechos a mano; sin letra, WER 23,2 % en JamendoLyrics y 26,5–40 % en gallego. Quedaban
anotados como flojos: el gallego sin letra, el gallego urbano con letra, la primera palabra de
la demo «laverca» (cae en la intro) y los coros solapados.

## Qué se miró (16/11/2026)

Artículos y modelos publicados hasta hoy, leídos en su fuente (fichas de Hugging Face y arXiv):

| Qué | Qué es | Licencia | Veredicto |
|---|---|---|---|
| [`mrfakename/w2v-bert-2.0-music-lyrics-ctc`](https://huggingface.co/mrfakename/w2v-bert-2.0-music-lyrics-ctc) (09/2026) | CTC de letras (921 caracteres, multilingüe) sobre un w2v-BERT 2.0 reentrenado con 47 500 h de música y ajustado con letras de canciones enteras | MIT | **medido y adoptado** (abajo). Su ficha no documenta los datos de entrenamiento |
| [`radiant-lyrics/sylla-600m-v1`](https://huggingface.co/radiant-lyrics/sylla-600m-v1) | el anterior ajustado con letras cronometradas a mano por sílabas; publica 95,9 % a ≤ 0,3 s en JamendoLyrics | GPL-3.0 | fuera por licencia (principio 8); su cifra queda por debajo de las nuestras |
| `hcX02/echora-mms-300m-…-lyrics-forced-aligner`, `tuneperfect/tunestudio-aligner` | MMS-300m ajustados a canto | solo uso no comercial | fuera por licencia |
| [`Qwen/Qwen3-ForcedAligner-0.6B`](https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B) y su ampliación a 112 idiomas (con gallego) | alineador no autorregresivo | Apache-2.0 | resolución de 80 ms y 5 min como máximo: no sirve para karaoke (vamos a 20 ms) |
| `cava-reader/cavaalign-v1` | alineador de 16 MB para audiolibros, 35 idiomas | AGPL-3.0 | fuera por licencia; hecho para habla leída |
| Montreal Forced Aligner 3.0, FA-Bench, FuseAlign (arXiv 2606.18466, 2609.32396, 2609.33650) | alineadores y bancos de habla | — | miden habla limpia; nada publicado supera a un CTC con Viterbi en canto |
| Durand et al. 2023 (Spotify), ElevenLabs «Cue» | referencias publicadas en JamendoLyrics: 94 % y 92,7 % a ≤ 0,3 s | — | por debajo de lo que ya teníamos (98,8 %) |
| [`BuzzASR/galician`](https://huggingface.co/BuzzASR/galician) (09/2026, EMNLP 2026) | Whisper large-v3 ajustado solo a gallego (FLEURS + Common Voice 25); el mejor CER abierto en habla gallega según su artículo | MIT | medido (abajo) |
| `BSC-LT/stt_los_conformer_transducer_large` (11/2026) | Conformer-Transducer es/ca/gl/eu | Apache-2.0 | pide NeMo y no da salida CTC; no se midió |
| «Exploiting Music Source Separation for ALT with Whisper» (arXiv 2506.15514) | trocear la canción por donde suena la voz separada: 23,0 → 20,4 % de WER en Jam-ALT, el mejor sistema abierto publicado | — | **adoptado**: es lo que hace ahora el transcriptor |
| [`Qwen/Qwen3-ASR`](https://huggingface.co/Qwen/Qwen3-ASR-0.6B-hf) (01/2026; en `transformers` desde 5.13) | modelo de audio entrenado también con canto y canciones; 30 idiomas, sin gallego | Apache-2.0 | medido el de 0,6B (abajo); el de 1,7B no cabe en 4 GB |

Proxecto Nós e HiTZ no han publicado modelos de voz gallegos nuevos desde `005`.

## Cómo se midió

El banco de siempre (`quick`, `jamendo`, `stress`, `gl`, `repeats`, `private`) y dos piezas nuevas
(C2), porque las cifras gallegas de `005` no decían lo que parecía:

- **Referencias por línea** (`karaoke-bench import-lrc`, `Timing = "lines"`). LRCLIB guarda letras
  sincronizadas a mano, línea a línea, de muchas canciones gallegas actuales. Con ellas se mide
  dónde empieza cada línea (lo que más se ve en un karaoke) en canciones que nadie va a
  cronometrar palabra a palabra: solo cuenta el inicio de la primera palabra de cada línea, y,
  como toda marca hecha a mano, vale a unas décimas (manda el % a ≤ 0,5 s). En local hay dos de la
  biblioteca del dueño: «Esta Vida Pide Outra» (Kid Mount, Yuly) y «Viaxei» (The Rapants).
- **WER tolerante** (gallego). Las webs escriben la gheada y el seseo como suenan («janarme»,
  «corasón») y los pronombres separados («deixei che»); un transcriptor que escribe la forma
  normativa de la misma palabra la oyó bien, y el WER estricto lo cuenta como fallo. El tolerante
  iguala gheada, seseo, tildes y pronombres juntos o separados. En «La Favorita» el WER pasa de
  38,7 % a 28,1 %: diez puntos eran ortografía.
- **Acuerdo entre modelos.** Las dos canciones urbanas con tiempos hechos a mano daban 74–79 % a
  ≤ 0,3 s. El modelo gallego de habla y el modelo de música, que no comparten nada, colocan
  «La Favorita» igual: el 97,5 % de las palabras a menos de 0,1 s uno de otro y el 100 % a menos
  de 0,3 s, y los dos puntúan 75 % contra esos tiempos, que van 0,12 s por delante. Ese 74–79 %
  era el límite de la referencia hecha a mano, no del alineador.

## Sincronía con letra

### Un segundo modelo, entrenado con canciones

El modelo de música, él solo y para los cuatro idiomas, iguala a los cuatro modelos de habla por
idioma, y cada uno falla en canciones distintas (en JamendoLyrics, 19 canciones mejoran con el de
música y 11 empeoran; eligiendo el mejor en cada una saldría 99,35 %). De ahí la mezcla: los dos
escuchan la voz, uno detrás de otro, y se promedian sus probabilidades (`emissions.blend`).

Se promedian probabilidades y no sus logaritmos. La primera prueba, con la media de logaritmos,
salió peor que cualquiera de los dos (99,2 % en `quick` y el 96 % de las palabras con confianza
menor de 0,3): un modelo CTC pone cada letra en uno o dos fotogramas y dos modelos casi nunca
eligen el mismo, así que la media geométrica deja todas las letras improbables en todas partes.
Con la media de probabilidades vale la letra que oiga cualquiera de los dos.

Cuánto pesa cada modelo (`second_weight`, el del de música), en `quick`: con 0,3, 99,6 % y finales
de palabra a 0,069 s; con 0,5, 99,5 % y 0,077 s; con 0,7, 99,5 % pero el inglés a 0,155 s de error
medio. Los finales del modelo de música son peores (su ficha lo avisa), así que pesa **0,3**.

| Con letra (≤ 0,3 s · error medio) | Modelo del idioma (`005`) | Música solo | **Mezcla (0,3, descanso 0,05)** |
|---|---|---|---|
| jamendo (79) | 98,8 % · 0,093 s | 99,1 % · 0,080 s | **99,3 % · 0,062 s** |
| jamendo: de / en / es / fr | 99,4 / 97,6 / 99,5 / 98,8 % | 99,6 / 98,4 / 99,8 / 98,7 % | **99,6 / 98,6 / 99,8 / 99,1 %** |
| jamendo: mediana · fin (mediana) · cobertura | 0,035 · 0,074 s · 92,3 % | 0,035 · 0,142 s · 92,8 % | 0,034 · 0,082 s · 92,9 % |
| quick (20) | 99,3 % · 0,064 s | 99,4 % · 0,072 s | **99,6 % · 0,056 s** |
| stress (24) | 99,2 % · 0,068 s | 99,3 % · 0,095 s | **99,6 % · 0,054 s** |
| gl (2 validadas) | 99,8 % · 0,016 s | 100,0 % · 0,013 s | 100,0 % · 0,015 s |
| «Viaxei», inicio de línea (≤ 0,3 · ≤ 0,5 s) | 92,3 · 94,9 % | 85,7 · 88,1 % | **95,1 · 97,6 %** |
| «Esta Vida Pide Outra», inicio de línea | 90,0 · 94,0 % | 86,5 · 96,2 % | 86,5 · **96,2 %** |

- En JamendoLyrics, 16 canciones suben más de un punto y ninguna empeora su mediana. Solo una
  baja más de un punto: «Fantasma» coloca seis «ah» que el modelo de habla se saltaba enteros y
  acierta más palabras en total, pero tres caen lejos (97,2 → 93,6 %). Suben, entre otras,
  «cool.cavemen» (el de música solo la dejaba en 83,9 %), «Pluie d'entre deux saisons», la peor
  francesa (89,6 → 91,2 %), «Peyote» y «Tom Orlando».
- El inglés, el idioma más flojo, sube un punto, y la media (las palabras que se van lejos) baja
  un tercio. La mediana sigue en 0,034 s (meta de `003`: 0,03).

### La forma de la canción la decide el modelo del idioma

La mezcla tal cual rompía lo de `016`. En el conjunto `repeats` (letras que escriben una vez lo
que se canta varias seguidas), las palabras bien colocadas bajaban del 88,5 % al 85,8 %, y del
87,4 % al 82,7 % sin marcas: en «Keep On» faltaba la segunda vuelta de un estribillo y su última
línea se estiraba encima. El modelo de música reparte su probabilidad en el tiempo (su ficha
avisa de que los finales de palabra no son fiables), y en la media estirar una línea sobre una
repetición sale más barato que pagar los 30 de volver atrás. Bajar ese coste a 20 o 15 apenas
ayudaba (85,8 → 86,6 %), y con un solo modelo y el descanso nuevo el conjunto quedaba idéntico,
así que la causa era la mezcla.

Ahora hay dos búsquedas. La primera, con el modelo del idioma solo, decide la forma de la
canción: cómo se lee cada marca «(x4)» y qué versos se cantan otra vez. La segunda, con los dos
modelos, recorre esos versos en ese orden (sin volver atrás y pudiendo saltarse alguno) y decide
dónde va cada palabra; una línea que la primera dejó fuera sigue en su sitio, y la mezcla aún
puede colocarla (`aligner._sung_order`). `LyricsAligner.version` = 16.

| `repeats` (88): palabras bien colocadas | Antes (`016`) | Mezcla en una búsqueda | **Dos búsquedas** |
|---|---|---|---|
| con «(xN)» | 89,5 % | 88,9 % | **89,6 %** |
| sin marca | 87,4 % | 82,7 % | **87,4 %** |

El error medio en ese conjunto sube un poco (0,101 → 0,119 s: coloca más palabras de las
difíciles) y en `quick` el resultado es idéntico al de una búsqueda.

### Descansar entre dos palabras de una línea cuesta un poco

Entre dos palabras de una línea el camino podía esperar gratis todo lo que quisiera. Una palabra
de una o dos letras encuentra algo parecido a ella en cualquier sitio, así que la «A» que abre la
demo «laverca» caía en la intro, ocho segundos antes de su línea (nota de C10 en `ESTADO.md`), y
en «Viaxei» una línea de coro «(Uh, u-u-uh…)» se estiraba 39 s sobre un instrumental.

Ahora ese descanso cuesta `rest_penalty` por cada fotograma en el que la voz calla
(`ctc._Layout.resting`: el blanco entre palabras y el separador de palabras). Barrido:

| `rest_penalty` | «A» de laverca | Lo demás |
|---|---|---|
| 0 (antes) | 23,3 s con el modelo de habla, 4,0 s con la mezcla (se canta en 31,9 s) | — |
| **0,05** | **31,9 s** | con la mezcla cambia menos de 0,1 puntos en JamendoLyrics, `quick` y `stress` |
| 0,1 | 31,9 s | igual que 0,05 con un modelo |
| 0,2 y 0,5 | 31,9 s | mueven palabras cortas en pausas de verdad: «Hola… ¿qué quieres?» con 2,4 s de pausa pasa de 0,56 s a 1,32 s (se canta en 0,54 s) |

Se queda en 0,05: lo justo para que una palabra no cruce un instrumental, sin tocar las pausas
de un par de segundos. No arregla todo: el «Ai» que abre una línea de «Esta Vida Pide Outra»
sigue 2 s antes de la marca hecha a mano (hay voz entre medias, y puede que se cante ahí), y un
coro de solo vocales sigue sin letras a las que agarrarse.

### Idiomas sin modelo propio

Antes los alineaba Omnilingual CTC 300M: 91,4 % a ≤ 0,3 s en `quick` y 71 % de cobertura
(`005`). El modelo de música solo, sin saber el idioma, da 99,4 % y 94,0 % en las mismas
canciones. Pasa a ser el modelo de cualquier idioma sin modelo propio cuya letra sepa escribir
(alfabetos latino, cirílico, griego, árabe, hebreo y tailandés, kana y kanji, y coreano por
letras: un bloque como «한» se deletrea con las tres que lo forman). Si no sabe escribir al
menos el 90 % de las letras de la letra, se usa Omnilingual, que conoce más alfabetos. Ningún
conjunto del banco tiene otros alfabetos: esa parte está probada con tests, no medida.

### Memoria y tiempo

El modelo de música tiene 581 millones de parámetros y se publica en 32 bits (2,3 GB).

- Con los dos modelos cargados a la vez, el alineador llegaba a 3,3 GB de VRAM y 5,5 GB de RAM.
  Ahora cada uno deja la tarjeta antes de que cargue el otro.
- La primera vez, el modelo de música se guarda en 16 bits en `~/.cache/karaoke/models/ctc/`
  (`emissions.half_copy`: 8 s, en un proceso aparte que pide 4,4 GB una sola vez) y se carga
  desde ahí. `karaoke-server prepare` lo deja hecho.

| Alinear (RTX 3050) | Antes | Ahora | Meta (`003`) |
|---|---|---|---|
| VRAM pico | 1,6 GB | 2,1 GB | ≤ 3 GB ✓ |
| RAM pico, una canción | 2,7 GB | 3,8 GB | ≤ 4 GB ✓ |
| RAM pico, 79 canciones en cuatro idiomas en un proceso (banco) | 3,7 GB | 4,0–4,3 GB | por encima, solo en el banco (el servidor hace cada canción en su proceso) |
| Tiempo por duración de la canción | 0,016 | 0,054 | — |
| Canción de 4 min con letra, con cargas | 60 s | 69–72 s | ≤ 2 min ✓ |
| «un aire» (4:47) con letra, `karaoke make` entero, dos pasadas | 83–87 s | 94–102 s | — |
| … de ello, alinear (comparte la CPU con la codificación del audio) | 12–14 s | 26–33 s | — |

En disco, el modelo de música ocupa 2,3 GB tal como se publica y 1,2 GB su copia en 16 bits.

## Sin letra

### Primero, la letra que ya existe

Lo que más mejora una canción sin letra pegada no es transcribirla mejor, sino no tener que
transcribirla. Dos canciones de la biblioteca del dueño («Viaxei» y «Esta Vida Pide Outra») se
hicieron pidiendo la letra a LRCLIB, LRCLIB las tiene con su duración exacta, y aun así salieron
transcritas a ciegas: la búsqueda preguntaba por el título del vídeo («The Rapants - Viaxei»),
que LRCLIB no conoce, y no encontraba nada.

`lyrics_lookup.find_lyrics` pregunta ahora, por orden: el nombre tal cual; el nombre de la
canción sin el artista delante o detrás, sin «(Official Video)» ni invitados (`song_names`); y
una búsqueda libre, quedándose solo con entradas de ese artista. Además de la misma edición
(±5 s) vale una entrada hasta un minuto más corta que el audio: un vídeo con una escena hablada
al principio o créditos al final canta la misma letra. Con los títulos reales de la biblioteca
encuentra «Viaxei» (247 s), «Esta Vida Pide Outra» (144 s), «Lisístrata» en su versión de vídeo
y «Non Me Culpes»; «Veráns» no está en LRCLIB.

La diferencia, en esas dos canciones: transcritas, el 22 % y el 58 % de las palabras salen mal;
con la letra de LRCLIB alineada, el 96 % y el 98 % de las líneas empiezan a menos de medio
segundo de donde las marcó una persona.

### Transcribir por tramos de canto

Whisper lee 30 s cada vez. Con la canción entera, su detector de habla (Silero, entrenado con
gente hablando) descarta pasajes cantados y sus ventanas cortan por mitad de las frases: en las
canciones del dueño faltaban trozos enteros (en «Viaxei», de 66 a 110 s y de 153 a 203 s). Como
en el mejor sistema abierto publicado (arXiv 2506.15514), la canción se le da ahora en tramos
cortados donde la voz separada descansa (`activity.voiced_stretches`): frases a menos de 0,5 s
se quedan juntas, los tramos crecen hasta el límite del modelo y una frase más larga que el
límite se corta por su pausa más larga.

Después, el alineador hace de **segundo oyente** (`aligner.heard`): una línea transcrita que él
oye con confianza casi nula donde la colocó (media geométrica de sus palabras por debajo de
`make.ASR_MIN_CONFIDENCE`) se la inventó el transcriptor, y no sale. En «Lisístrata», tres
líneas inventadas («Descoberte de novidades descobertadas a bordo de nós…») quedan en 0,04–0,06;
las cantadas, entre 0,4 y 0,99.

Las referencias de las canciones de la biblioteca se rehicieron para medir esto: «Veráns» con la
letra que pegó el dueño y «Lisístrata» con la completa, las dos con las repeticiones escritas
(antes salían de un `karaoke.json`, al que le faltaban las líneas que el alineador se saltó).
WER tolerante (`bench/data/tools/rescore_asr.py`, local), de la transcripción y del texto que
queda en el karaoke tras alinear y filtrar:

| Gallego sin letra | Urbanas (6): transcripción · texto final | Públicas (5): transcripción · texto final |
|---|---|---|
| HiTZ, canción entera (antes) | 40,1 % · 39,8 % | 32,5 % · 32,4 % |
| **HiTZ, tramos de 28 s, alineador nuevo, filtro 0,05** | 40,3 % · **36,8 %** | 32,0 % · **30,8 %** |
| BuzzASR, canción entera | 40,1 % · 40,1 % | 30,6 % · 30,5 % |
| BuzzASR, tramos de 28 s, filtro 0,05 | 41,8 % · 37,3 % | 31,4 % · 29,5 % |
| BuzzASR, tramos de 12 s | 41,4 % | 30,3 % |
| HiTZ, tramos de 12 s / 8 s | 44,5 % / 51,1 % | 35,5 % / 37,2 % |
| Nós turbo, tramos de 28 s / 12 s | 50,2 % / 46,7 % | 36,2 % / 31,6 % |

- Por tramos, Whisper borra menos (palabras que no escribe: 16,8 → 10,0 % en las urbanas) e
  inventa más (3,7 → 9,6 %); el filtro quita lo inventado. Juntos, 3 puntos menos en las urbanas
  y 1,6 en las públicas.
- El umbral del filtro (`ASR_MIN_CONFIDENCE` = 0,05) se eligió con el alineador final: las líneas
  por debajo de 0,05 son en un 84 % texto mal oído y llevan el 0,7 % de las palabras bien
  oídas. Con 0,08 el gallego queda igual y los otros idiomas pierden medio punto.

### Lo que no cambia

- **El modelo gallego sigue siendo HiTZ.** BuzzASR, el mejor en habla gallega según su artículo,
  empata con él en canciones, entero o por tramos; el Whisper turbo de Nós queda por detrás.
  Regla del plan: en empate se queda lo que hay.
- **Tramos más cortos no ayudan a los modelos grandes** (12 s: +4 puntos; 8 s: +11): pierden el
  contexto. A los turbo sí, y por eso cada modelo lleva su límite (`WhisperSpec.stretch`).

### Los otros idiomas

| Sin letra, Whisper large-v3-turbo | quick (20) | jamendo (79) | jamendo, inglés |
|---|---|---|---|
| canción entera (antes) | 21,7 % | 23,2 % | 33,5 % |
| tramos de 28 s | 20,8 % | — | — |
| **tramos de 12 s** | **18,6 %** | **21,3 %** | **27,4 %** |
| tramos de 12 s, texto final con el filtro | 17,7 % | — | — |
| Qwen3-ASR 0,6B, tramos de 28 s | 20,7 % | — | 22,9 % |

- En JamendoLyrics, 21 canciones mejoran más de 5 puntos y 10 empeoran; ninguna cambia de
  idioma. Una canción de 4 min sin letra tarda 73 s en vez de 65 s solo por los tramos; con el
  alineador nuevo detrás, 83 s (90 s en gallego, que transcribe con HiTZ large).
- Qwen3-ASR (entrenado también con canciones) es el mejor en inglés, 4,5 puntos por debajo de
  Whisper, y peor en castellano, alemán y francés. No entra: sería un segundo motor de
  transcripción para un solo idioma que no es la prioridad del proyecto. Queda medido y anotado
  abajo.

## Decisión

- **Alineador** (`LyricsAligner.version` = 16): el modelo de cada idioma con el de música como
  segundo oyente (`DEFAULT_SECOND`, peso 0,3; el primero decide las repeticiones y las marcas),
  descanso entre palabras a 0,05 por fotograma de silencio, y el de música solo para los idiomas sin modelo propio (`FALLBACK_MODEL`; Omnilingual
  queda como `WIDE_FALLBACK_MODEL` para otros alfabetos y para los subtítulos de entrevistas).
- **Transcripción** (`WhisperTranscriber.version` = 6): por tramos de canto, 28 s para los
  modelos grandes y 12 s para los turbo (`WhisperSpec.stretch`); HiTZ sigue para el gallego.
- **Filtro** de líneas transcritas que el alineador no oye (`make.ASR_MIN_CONFIDENCE` = 0,05).
- **LRCLIB** encuentra las canciones que vienen de un vídeo (`lyrics_lookup.song_names`).
- **Banco**: `import-lrc` y referencias por línea; WER tolerante para el gallego.
- Pipelines del barrido en `bench/pipelines/rev-*.toml`; informes en `bench/results/2026-11-1[67]-*`
  (los de las canciones privadas, solo en local).

Confirmado el 17/11 con `c4-default` tal como quedó (alineador 16, transcriptor 6;
`bench/results/2026-11-17-c4-default-*`): las mismas cifras al decimal que las pipelines del
barrido, con letra en `stress`, `gl`, `jamendo` y las privadas, y sin letra en `gl`, `quick`,
`jamendo` y las privadas. Los informes de `quick` y `jamendo` con letra marcan 3,3 GB de VRAM, y
no es el alineador: el banco mide la memoria de toda la tarjeta, algo más la ocupó durante la
ejecución de `quick`, y la de `jamendo` reutiliza esas canciones con su pico. La memoria de la
tarjeta no depende de la letra (la búsqueda va en la CPU), y las mismas canciones sin letra, igual
que `stress` y `gl`, se quedan en 2,1–2,3 GB.

## Lo que queda por debajo de lo mejor

- **Gallego sin letra.** El texto final se queda en un 31 % de palabras mal en las canciones
  públicas y un 37 % en las urbanas. En las dos con letra publicada con las que `003` fijó la meta
  (690 palabras, WER estricto de la transcripción), 26,5 → 25,9 % frente al 35,9 % de la base: la
  meta (≤ 25,1 %) sigue sin cumplirse, ahora por 0,8 puntos. Ningún modelo
  publicado se entrenó con canto en gallego, y los tres que hay (HiTZ, BuzzASR, Nós) fallan en lo
  mismo. Lo único que lo bajaría de verdad es ajustar uno con canciones gallegas cantadas, y no
  existe un conjunto abierto de ellas; se podría construir en local con las letras de LRCLIB y
  el audio propio del dueño, sin publicarlo. Mientras, la vía buena es la letra: pegada o de
  LRCLIB, que ahora sí se encuentra.
- **Coros de solo vocales** («Uh, u-u-uh…»): sin letras a las que agarrarse, se estiran sobre
  instrumentales donde el separador deja algo de voz o se colocan en otro estribillo.
- **Inglés sin letra**: Qwen3-ASR 0,6B transcribe 4,5 puntos mejor que Whisper; medido y no
  adoptado (arriba).
- **Mediana de inicio** en JamendoLyrics: 0,034 s frente a la meta de 0,03.
- **Medir el gallego**: siguen validadas solo dos canciones públicas, más dos urbanas con tiempos
  por línea. Cada canción de la biblioteca que tenga letra sincronizada en LRCLIB se puede añadir
  sin trabajo (`import-lrc`), si la entrada es de la misma grabación (la de «Lisístrata» va 19 s
  por delante del vídeo).
- **Sin medir**: el respaldo de otros alfabetos (solo tests) y la separación de voces, que esta
  revisión no tocó.

## Consecuencias

- Motor: los cambios de arriba; contratos, API y web no cambian. `karaoke-server prepare` baja
  también el modelo de música y hace su copia en 16 bits (pide 4,4 GB de RAM libres una vez).
- Banco (C2): `import-lrc`, `Timing = "lines"`, columna «WER tolerante», `QwenTranscriber` en
  `karaoke_bench.baseline.qwen` para comparar.
- `NOTICE.md`, `docs/lyrics-sync.md`, `docs/benchmark.md` y `docs/languages-and-models.md` al día.
