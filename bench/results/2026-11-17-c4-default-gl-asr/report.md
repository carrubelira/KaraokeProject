# Banco · c4-default · gl · sin letra

- Fecha: 2026-11-17T15:30:31+01:00
- Commit: 3b31efe
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

Mel-Band RoFormer (Kim, 8 s) + Whisper by stretches of singing (HiTZ large-v3 for Galician, large-v3-turbo otherwise) + lyrics aligner (each language's CTC model with the music model as a second listener)

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v6
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v16

## Resumen

| Grupo | Canciones | Fallos | WER | WER tolerante | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gl | 5 | 0 | 33.0 % | 32.0 % | 16.3 % | 0.020 | 0.016 | 99.8 % | 99.8 % | 0.020 | 0.010 | 86.7 % | — | 0 | 90 | 0.0 % | 22.0 % |
| total | 5 | 0 | 33.0 % | 32.0 % | 16.3 % | 0.020 | 0.016 | 99.8 % | 99.8 % | 0.020 | 0.010 | 86.7 % | — | 0 | 90 | 0.0 % | 22.0 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 8.2 | 2867 | 2372 | 0.205 |
| transcriber | 0.1 | 3319 | 2422 | 0.079 |
| segmenter | — | 0 | 77 | 0.000 |
| aligner | 0.1 | 2131 | 3850 | 0.058 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pantis-un-aire | gl | 287 | 29.6 % | 28.3 % | 0.020 | 99.6 % | 99.6 % | 83.2 % | validada (75.7 %) | 0.0 % | 13.3 % | gl | 160.4 |  |
| cibran-o-mundo-do-motor | gl | 195 | 19.1 % | 17.1 % | — | — | — | — | sin validar | 0.0 % | 9.2 % | gl | 66.2 |  |
| cloplas-laverca | gl | 313 | 16.9 % | 16.6 % | 0.020 | 100.0 % | 100.0 % | 90.8 % | validada (75.1 %) | 0.0 % | 4.8 % | gl | 106.7 |  |
| fanny-alexander-lene | gl | 244 | 65.2 % | 65.7 % | — | — | — | — | sin validar | 0.0 % | 38.6 % | gl | 77.8 |  |
| mortos-en-vida-chapapote | gl | 162 | 50.2 % | 49.1 % | — | — | — | — | sin validar | 0.0 % | 44.1 % | gl | 117.8 |  |

## Peores casos

Mayor mediana de error de inicio:
- cloplas-laverca: 0.020 s
- pantis-un-aire: 0.020 s

Mayor WER:
- fanny-alexander-lene: 65.2 %
- mortos-en-vida-chapapote: 50.2 %
- pantis-un-aire: 29.6 %
- cibran-o-mundo-do-motor: 19.1 %
- cloplas-laverca: 16.9 %

## Notas

- Referencia semiautomática validada de oído en pantis-un-aire, cloplas-laverca: fiable a unos ±0,1 s, así que ahí manda el % ≤ 0,3 s más que la mediana. Solo cuentan las líneas marcadas «bien» (columna Referencia).
- Referencia sin validar de oído en cibran-o-mundo-do-motor, fanny-alexander-lene, mortos-en-vida-chapapote: no cuenta para la sincronía hasta que se valide.
- WER tolerante (gallego): no cuenta como error escribir de otra forma la misma palabra: gheada («janarme» / «ganarme»), seseo («corasón» / «corazón»), tildes y pronombres juntos o separados del verbo («deixei che» / «deixeiche»).
- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
