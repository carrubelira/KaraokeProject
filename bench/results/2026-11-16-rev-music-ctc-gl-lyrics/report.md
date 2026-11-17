# Banco · rev-music-ctc · gl · con letra

- Fecha: 2026-11-16T13:41:23+01:00
- Commit: a85e232-dirty
- Banco 3.0.0, normalización v1
- Referencias: gl semiautomática

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

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gl | 5 | 0 | — | — | 0.016 | 0.013 | 100.0 % | 100.0 % | 0.040 | 0.003 | 100.0 % | — | 0 | 71 | 0.1 % | 43.7 % |
| total | 5 | 0 | — | — | 0.016 | 0.013 | 100.0 % | 100.0 % | 0.040 | 0.003 | 100.0 % | — | 0 | 71 | 0.1 % | 43.7 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 8.2 | 2867 | 2372 | 0.205 |
| aligner | 6.4 | 2129 | 4264 | 0.032 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pantis-un-aire | gl | 287 | — | 0.020 | 100.0 % | 100.0 % | 100.0 % | validada (75.7 %) | 0.0 % | 15.4 % | — | 69.5 |  |
| cibran-o-mundo-do-motor | gl | 195 | — | — | — | — | — | sin validar | 0.1 % | 17.7 % | — | 45.6 |  |
| cloplas-laverca | gl | 313 | — | 0.011 | 100.0 % | 100.0 % | 100.0 % | validada (75.1 %) | 0.2 % | 55.0 % | — | 74.8 |  |
| fanny-alexander-lene | gl | 244 | — | — | — | — | — | sin validar | 0.0 % | 64.3 % | — | 57.9 |  |
| mortos-en-vida-chapapote | gl | 162 | — | — | — | — | — | sin validar | 0.1 % | 65.9 % | — | 38.1 |  |

## Peores casos

Mayor mediana de error de inicio:
- pantis-un-aire: 0.020 s
- cloplas-laverca: 0.011 s

## Notas

- Referencia semiautomática validada de oído en pantis-un-aire, cloplas-laverca: fiable a unos ±0,1 s, así que ahí manda el % ≤ 0,3 s más que la mediana. Solo cuentan las líneas marcadas «bien» (columna Referencia).
- Referencia sin validar de oído en cibran-o-mundo-do-motor, fanny-alexander-lene, mortos-en-vida-chapapote: no cuenta para la sincronía hasta que se valide.
- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
