# Banco · rev-blend · stress · con letra

- Fecha: 2026-11-16T18:45:41+01:00
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

Mel-Band RoFormer (Kim, 8 s) + Whisper + lyrics aligner (each language's CTC model averaged with w2v-BERT 2.0 music lyrics CTC)

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v5
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v14 {'second': 'music-w2vbert-ctc'}

## Resumen

| Grupo | Canciones | Fallos | WER | WER tolerante | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| adlib | 4 | 0 | — | — | — | 0.029 | 0.099 | 98.4 % | 98.7 % | 0.078 | -0.062 | 91.5 % | — | 0 | 73 | 0.0 % | 20.0 % |
| echo | 4 | 0 | — | — | — | 0.048 | 0.064 | 99.6 % | 99.7 % | 0.123 | 0.035 | 97.6 % | — | 0 | 70 | 0.0 % | 15.0 % |
| extra-lines | 4 | 0 | — | — | — | 0.027 | 0.040 | 99.6 % | 99.8 % | 0.091 | -0.001 | 97.2 % | — | 0 | 70 | 0.1 % | 12.8 % |
| gap | 4 | 0 | — | — | — | 0.021 | 0.031 | 99.9 % | 100.0 % | 0.080 | 0.008 | 96.6 % | — | 0 | 70 | 0.1 % | 11.9 % |
| missing-line | 4 | 0 | — | — | — | 0.028 | 0.040 | 99.8 % | 100.0 % | 0.093 | 0.019 | 93.3 % | — | 0 | 70 | 0.0 % | 20.6 % |
| web | 4 | 0 | — | — | — | 0.039 | 0.047 | 99.8 % | 99.9 % | 0.052 | 0.027 | 92.8 % | — | 0 | 73 | 0.0 % | 18.4 % |
| total | 24 | 0 | — | — | — | 0.030 | 0.054 | 99.5 % | 99.6 % | 0.080 | 0.002 | 94.6 % | — | 0 | 71 | 0.0 % | 16.4 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 8.5 | 2867 | 2346 | 0.206 |
| aligner | 0.1 | 2133 | 3865 | 0.052 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| adlib-der-musiker | de | 271 | — | — | 0.020 | 99.1 % | 99.4 % | 98.0 % | manual | 0.0 % | 11.3 % | — | 80.4 |  |
| adlib-pas-que-tes-pas | fr | 202 | — | — | 0.031 | 100.0 % | 100.0 % | 88.1 % | manual | 0.0 % | 32.3 % | — | 53.5 |  |
| adlib-ridgway | en | 284 | — | — | 0.047 | 93.2 % | 93.6 % | 77.0 % | manual | 0.1 % | 28.2 % | — | 73.4 |  |
| adlib-te-recuerdo | es | 194 | — | — | 0.029 | 99.8 % | 100.0 % | 98.3 % | manual | 0.0 % | 8.3 % | — | 52.3 |  |
| echo-cafe-jenseitz | de | 248 | — | — | 0.056 | 97.7 % | 98.9 % | 94.6 % | manual | 0.0 % | 15.1 % | — | 63.0 |  |
| echo-cortez | en | 241 | — | — | 0.074 | 100.0 % | 100.0 % | 98.9 % | manual | 0.0 % | 8.2 % | — | 62.1 |  |
| echo-hablame | es | 214 | — | — | 0.030 | 100.0 % | 100.0 % | 99.1 % | manual | 0.0 % | 26.4 % | — | 54.8 |  |
| echo-mere-nature | fr | 225 | — | — | 0.036 | 99.6 % | 99.6 % | 96.5 % | manual | 0.0 % | 10.3 % | — | 58.9 |  |
| extra-lines-der-musiker | de | 271 | — | — | 0.020 | 99.1 % | 99.4 % | 98.0 % | manual | 0.0 % | 11.3 % | — | 69.3 |  |
| extra-lines-esencia | es | 262 | — | — | 0.023 | 99.7 % | 100.0 % | 98.2 % | manual | 0.0 % | 13.2 % | — | 67.1 |  |
| extra-lines-kinematic | en | 183 | — | — | 0.053 | 100.0 % | 100.0 % | 93.9 % | manual | 0.3 % | 20.3 % | — | 47.2 |  |
| extra-lines-mere-nature | fr | 225 | — | — | 0.036 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 6.3 % | — | 58.1 |  |
| gap-capotes | fr | 218 | — | — | 0.025 | 100.0 % | 100.0 % | 97.6 % | manual | 0.0 % | 10.9 % | — | 56.5 |  |
| gap-esencia | es | 292 | — | — | 0.023 | 99.7 % | 100.0 % | 98.2 % | manual | 0.0 % | 12.6 % | — | 74.8 |  |
| gap-keine-lust | de | 259 | — | — | 0.016 | 100.0 % | 100.0 % | 95.8 % | manual | 0.0 % | 1.7 % | — | 67.4 |  |
| gap-kinematic | en | 213 | — | — | 0.053 | 100.0 % | 100.0 % | 93.9 % | manual | 0.3 % | 22.4 % | — | 54.6 |  |
| missing-line-baila | es | 210 | — | — | 0.019 | 100.0 % | 100.0 % | 96.1 % | manual | 0.0 % | 24.1 % | — | 54.3 |  |
| missing-line-le-musee | fr | 184 | — | — | 0.020 | 100.0 % | 100.0 % | 91.4 % | manual | 0.0 % | 8.6 % | — | 47.9 |  |
| missing-line-sehnsucht | de | 233 | — | — | 0.029 | 100.0 % | 100.0 % | 93.4 % | manual | 0.0 % | 15.8 % | — | 59.7 |  |
| missing-line-the-rinn | en | 231 | — | — | 0.068 | 98.9 % | 100.0 % | 91.6 % | manual | 0.0 % | 33.9 % | — | 58.6 |  |
| web-1-freak | de | 188 | — | — | 0.048 | 100.0 % | 100.0 % | 97.8 % | manual | 0.0 % | 11.7 % | — | 52.9 |  |
| web-10-disparan | es | 160 | — | — | 0.024 | 99.5 % | 100.0 % | 100.0 % | manual | 0.0 % | 18.0 % | — | 41.0 |  |
| web-confession | fr | 148 | — | — | 0.030 | 99.3 % | 99.3 % | 87.2 % | manual | 0.2 % | 20.1 % | — | 40.9 |  |
| web-wordsmith | en | 171 | — | — | 0.047 | 100.0 % | 100.0 % | 90.5 % | manual | 0.0 % | 23.8 % | — | 44.5 |  |

## Peores casos

Mayor mediana de error de inicio:
- echo-cortez: 0.074 s
- missing-line-the-rinn: 0.068 s
- echo-cafe-jenseitz: 0.056 s
- extra-lines-kinematic: 0.053 s
- gap-kinematic: 0.053 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
