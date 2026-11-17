# Banco · rev-music-ctc · stress · con letra

- Fecha: 2026-11-16T13:53:25+01:00
- Commit: a85e232-dirty
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

Mel-Band RoFormer (Kim, 8 s) + Whisper + lyrics aligner (w2v-BERT 2.0 music lyrics CTC for every language)

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v5
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v14 {'model': 'music-w2vbert-ctc'}

## Resumen

| Grupo | Canciones | Fallos | WER | WER tolerante | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| adlib | 4 | 0 | — | — | — | 0.027 | 0.168 | 98.1 % | 98.2 % | 0.118 | -0.040 | 90.3 % | — | 0 | 74 | 0.1 % | 25.5 % |
| echo | 4 | 0 | — | — | — | 0.046 | 0.065 | 99.4 % | 100.0 % | 0.184 | 0.047 | 97.6 % | — | 0 | 73 | 0.0 % | 22.8 % |
| extra-lines | 4 | 0 | — | — | — | 0.024 | 0.089 | 99.8 % | 99.8 % | 0.130 | 0.056 | 96.6 % | — | 0 | 73 | 0.1 % | 16.9 % |
| gap | 4 | 0 | — | — | — | 0.022 | 0.099 | 99.7 % | 99.8 % | 0.127 | 0.078 | 96.6 % | — | 0 | 74 | 0.1 % | 24.6 % |
| missing-line | 4 | 0 | — | — | — | 0.032 | 0.087 | 99.5 % | 99.8 % | 0.148 | 0.070 | 92.9 % | — | 0 | 73 | 0.0 % | 32.2 % |
| web | 4 | 0 | — | — | — | 0.036 | 0.050 | 99.7 % | 99.8 % | 0.083 | 0.026 | 92.0 % | — | 0 | 75 | 0.1 % | 23.4 % |
| total | 24 | 0 | — | — | — | 0.029 | 0.095 | 99.3 % | 99.5 % | 0.121 | 0.036 | 94.0 % | — | 0 | 73 | 0.1 % | 24.2 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 8.5 | 2867 | 2346 | 0.206 |
| aligner | 8.0 | 2133 | 3262 | 0.032 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| adlib-der-musiker | de | 271 | — | — | 0.021 | 98.8 % | 98.8 % | 96.3 % | manual | 0.0 % | 19.5 % | — | 66.0 |  |
| adlib-pas-que-tes-pas | fr | 202 | — | — | 0.026 | 98.3 % | 98.3 % | 88.1 % | manual | 0.1 % | 35.1 % | — | 47.9 |  |
| adlib-ridgway | en | 284 | — | — | 0.044 | 93.3 % | 93.3 % | 73.4 % | manual | 0.2 % | 39.9 % | — | 67.5 |  |
| adlib-te-recuerdo | es | 194 | — | — | 0.028 | 99.8 % | 100.0 % | 98.3 % | manual | 0.0 % | 7.2 % | — | 46.4 |  |
| echo-cafe-jenseitz | de | 248 | — | — | 0.077 | 98.9 % | 100.0 % | 94.6 % | manual | 0.0 % | 33.3 % | — | 57.8 |  |
| echo-cortez | en | 241 | — | — | 0.077 | 98.9 % | 100.0 % | 98.9 % | manual | 0.0 % | 7.6 % | — | 57.2 |  |
| echo-hablame | es | 214 | — | — | 0.032 | 100.0 % | 100.0 % | 99.1 % | manual | 0.0 % | 39.6 % | — | 50.1 |  |
| echo-mere-nature | fr | 225 | — | — | 0.025 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 10.7 % | — | 53.2 |  |
| extra-lines-der-musiker | de | 271 | — | — | 0.021 | 99.7 % | 99.7 % | 96.3 % | manual | 0.0 % | 19.5 % | — | 64.4 |  |
| extra-lines-esencia | es | 262 | — | — | 0.021 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 21.9 % | — | 62.2 |  |
| extra-lines-kinematic | en | 183 | — | — | 0.056 | 99.3 % | 99.3 % | 93.9 % | manual | 0.4 % | 20.3 % | — | 43.1 |  |
| extra-lines-mere-nature | fr | 225 | — | — | 0.025 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 6.0 % | — | 53.3 |  |
| gap-capotes | fr | 218 | — | — | 0.022 | 99.6 % | 100.0 % | 97.6 % | manual | 0.1 % | 49.6 % | — | 52.1 |  |
| gap-esencia | es | 292 | — | — | 0.021 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 24.0 % | — | 69.8 |  |
| gap-keine-lust | de | 259 | — | — | 0.019 | 99.6 % | 99.6 % | 95.8 % | manual | 0.0 % | 2.3 % | — | 62.5 |  |
| gap-kinematic | en | 213 | — | — | 0.055 | 99.3 % | 99.3 % | 93.9 % | manual | 0.4 % | 22.4 % | — | 50.4 |  |
| missing-line-baila | es | 210 | — | — | 0.024 | 100.0 % | 100.0 % | 96.1 % | manual | 0.0 % | 33.1 % | — | 50.0 |  |
| missing-line-le-musee | fr | 184 | — | — | 0.020 | 100.0 % | 100.0 % | 91.4 % | manual | 0.0 % | 24.9 % | — | 43.8 |  |
| missing-line-sehnsucht | de | 233 | — | — | 0.040 | 100.0 % | 100.0 % | 89.4 % | manual | 0.0 % | 36.4 % | — | 54.9 |  |
| missing-line-the-rinn | en | 231 | — | — | 0.075 | 97.9 % | 98.9 % | 93.1 % | manual | 0.0 % | 34.4 % | — | 54.0 |  |
| web-1-freak | de | 188 | — | — | 0.058 | 100.0 % | 100.0 % | 97.8 % | manual | 0.0 % | 19.9 % | — | 48.3 |  |
| web-10-disparan | es | 160 | — | — | 0.025 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 34.0 % | — | 37.0 |  |
| web-confession | fr | 148 | — | — | 0.027 | 98.6 % | 98.9 % | 83.3 % | manual | 0.2 % | 16.6 % | — | 37.2 |  |
| web-wordsmith | en | 171 | — | — | 0.036 | 100.0 % | 100.0 % | 90.7 % | manual | 0.0 % | 23.0 % | — | 40.4 |  |

## Peores casos

Mayor mediana de error de inicio:
- echo-cafe-jenseitz: 0.077 s
- echo-cortez: 0.077 s
- missing-line-the-rinn: 0.075 s
- web-1-freak: 0.058 s
- extra-lines-kinematic: 0.056 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
