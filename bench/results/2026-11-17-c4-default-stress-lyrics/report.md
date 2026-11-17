# Banco · c4-default · stress · con letra

- Fecha: 2026-11-17T14:40:03+01:00
- Commit: 3b31efe
- Banco 3.0.0, normalización v1
- Referencias: de manual, en manual, es manual, fr manual

## Entorno

| Clave | Valor |
|---|---|
| ctranslate2 | 4.8.5 |
| demucs | 4.0.1 |
| driver | 617.42 |
| faster-whisper | 1.2.1 |
| gpu | NVIDIA GeForce RTX 3050 Laptop GPU |
| gpu_memory_mb | 4096 |
| jiwer | 4.0.0 |
| numpy | 2.5.4 |
| platform | Linux-6.6.114.1-microsoft-standard-WSL2-x86_64-with-glibc2.43 |
| python | 3.12.16 |
| torch | 2.14.1+cu130 |
| transformers | 5.22.1 |

## Pipeline

Mel-Band RoFormer (Kim, 8 s) + Whisper by stretches of singing (HiTZ large-v3 for Galician, large-v3-turbo otherwise) + lyrics aligner (each language's CTC model with the music model as a second listener)

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v6
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v16

## Resumen

| Grupo | Canciones | Fallos | WER | WER tolerante | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| adlib | 4 | 0 | — | — | — | 0.030 | 0.099 | 98.5 % | 98.7 % | 0.068 | -0.058 | 91.3 % | — | 0 | 74 | 0.0 % | 24.1 % |
| echo | 4 | 0 | — | — | — | 0.047 | 0.064 | 99.5 % | 99.6 % | 0.107 | 0.033 | 97.6 % | — | 0 | 71 | 0.0 % | 16.6 % |
| extra-lines | 4 | 0 | — | — | — | 0.027 | 0.036 | 100.0 % | 100.0 % | 0.083 | 0.002 | 96.9 % | — | 0 | 72 | 0.1 % | 18.5 % |
| gap | 4 | 0 | — | — | — | 0.021 | 0.031 | 100.0 % | 100.0 % | 0.073 | 0.008 | 96.6 % | — | 0 | 72 | 0.1 % | 15.8 % |
| missing-line | 4 | 0 | — | — | — | 0.028 | 0.040 | 99.8 % | 100.0 % | 0.082 | 0.016 | 93.3 % | — | 0 | 72 | 0.0 % | 23.9 % |
| web | 4 | 0 | — | — | — | 0.040 | 0.048 | 99.9 % | 99.9 % | 0.045 | 0.029 | 92.7 % | — | 0 | 75 | 0.0 % | 26.8 % |
| total | 24 | 0 | — | — | — | 0.031 | 0.054 | 99.6 % | 99.7 % | 0.071 | 0.003 | 94.4 % | — | 0 | 72 | 0.0 % | 21.0 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 8.5 | 2867 | 2346 | 0.206 |
| aligner | 0.1 | 2295 | 3968 | 0.059 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| adlib-der-musiker | de | 271 | — | — | 0.021 | 100.0 % | 100.0 % | 97.2 % | manual | 0.0 % | 11.1 % | — | 94.4 |  |
| adlib-pas-que-tes-pas | fr | 202 | — | — | 0.034 | 100.0 % | 100.0 % | 88.1 % | manual | 0.0 % | 34.3 % | — | 55.7 |  |
| adlib-ridgway | en | 284 | — | — | 0.047 | 93.2 % | 93.6 % | 77.0 % | manual | 0.0 % | 34.9 % | — | 75.2 |  |
| adlib-te-recuerdo | es | 194 | — | — | 0.029 | 99.3 % | 99.6 % | 98.3 % | manual | 0.0 % | 16.0 % | — | 53.1 |  |
| echo-cafe-jenseitz | de | 248 | — | — | 0.055 | 97.7 % | 98.9 % | 94.6 % | manual | 0.0 % | 11.8 % | — | 64.3 |  |
| echo-cortez | en | 241 | — | — | 0.067 | 99.7 % | 99.7 % | 98.9 % | manual | 0.0 % | 12.4 % | — | 63.3 |  |
| echo-hablame | es | 214 | — | — | 0.030 | 99.0 % | 99.0 % | 99.1 % | manual | 0.0 % | 26.4 % | — | 55.6 |  |
| echo-mere-nature | fr | 225 | — | — | 0.038 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 15.9 % | — | 60.2 |  |
| extra-lines-der-musiker | de | 271 | — | — | 0.021 | 100.0 % | 100.0 % | 97.2 % | manual | 0.0 % | 11.4 % | — | 71.4 |  |
| extra-lines-esencia | es | 262 | — | — | 0.023 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 18.0 % | — | 68.6 |  |
| extra-lines-kinematic | en | 183 | — | — | 0.051 | 100.0 % | 100.0 % | 93.9 % | manual | 0.2 % | 30.8 % | — | 48.0 |  |
| extra-lines-mere-nature | fr | 225 | — | — | 0.037 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 13.9 % | — | 59.4 |  |
| gap-capotes | fr | 218 | — | — | 0.025 | 100.0 % | 100.0 % | 97.6 % | manual | 0.0 % | 9.3 % | — | 57.8 |  |
| gap-esencia | es | 292 | — | — | 0.023 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 17.4 % | — | 76.3 |  |
| gap-keine-lust | de | 259 | — | — | 0.015 | 100.0 % | 100.0 % | 95.8 % | manual | 0.0 % | 4.6 % | — | 71.0 |  |
| gap-kinematic | en | 213 | — | — | 0.050 | 100.0 % | 100.0 % | 93.9 % | manual | 0.2 % | 32.2 % | — | 55.5 |  |
| missing-line-baila | es | 210 | — | — | 0.019 | 100.0 % | 100.0 % | 96.1 % | manual | 0.0 % | 25.9 % | — | 55.9 |  |
| missing-line-le-musee | fr | 184 | — | — | 0.022 | 100.0 % | 100.0 % | 91.4 % | manual | 0.0 % | 8.6 % | — | 48.9 |  |
| missing-line-sehnsucht | de | 233 | — | — | 0.030 | 100.0 % | 100.0 % | 93.4 % | manual | 0.0 % | 15.8 % | — | 62.2 |  |
| missing-line-the-rinn | en | 231 | — | — | 0.056 | 98.9 % | 100.0 % | 91.6 % | manual | 0.0 % | 45.5 % | — | 59.8 |  |
| web-1-freak | de | 188 | — | — | 0.044 | 100.0 % | 100.0 % | 97.8 % | manual | 0.0 % | 21.6 % | — | 54.5 |  |
| web-10-disparan | es | 160 | — | — | 0.024 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 22.7 % | — | 42.2 |  |
| web-confession | fr | 148 | — | — | 0.029 | 99.3 % | 99.3 % | 87.2 % | manual | 0.2 % | 28.5 % | — | 41.9 |  |
| web-wordsmith | en | 171 | — | — | 0.050 | 100.0 % | 100.0 % | 90.2 % | manual | 0.0 % | 34.5 % | — | 45.8 |  |

## Peores casos

Mayor mediana de error de inicio:
- echo-cortez: 0.067 s
- missing-line-the-rinn: 0.056 s
- echo-cafe-jenseitz: 0.055 s
- extra-lines-kinematic: 0.051 s
- web-wordsmith: 0.050 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
