# Banco · rev-asr-voice12 · gl · sin letra

- Fecha: 2026-11-17T00:57:40+01:00
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

Mel-Band RoFormer (Kim, 8 s) + Whisper (each language's default) reading stretches of singing of at most 12 s + line segmenter + lyrics aligner

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v5 {'by_voice': True, 'stretch_seconds': 12.0}
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v14 {'second': '', 'rest_penalty': 0.0}

## Resumen

| Grupo | Canciones | Fallos | WER | WER tolerante | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gl | 5 | 0 | 36.5 % | 35.5 % | 19.1 % | 0.020 | 0.016 | 99.8 % | 100.0 % | 0.020 | 0.010 | 85.7 % | — | 0 | 95 | 0.0 % | 22.7 % |
| total | 5 | 0 | 36.5 % | 35.5 % | 19.1 % | 0.020 | 0.016 | 99.8 % | 100.0 % | 0.020 | 0.010 | 85.7 % | — | 0 | 95 | 0.0 % | 22.7 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 8.2 | 2867 | 2372 | 0.205 |
| transcriber | 0.1 | 3319 | 2419 | 0.137 |
| segmenter | — | 0 | 76 | 0.000 |
| aligner | 0.1 | 1555 | 2734 | 0.017 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pantis-un-aire | gl | 287 | 34.1 % | 32.1 % | 0.020 | 99.6 % | 100.0 % | 81.8 % | validada (75.7 %) | 0.0 % | 16.3 % | gl | 170.1 |  |
| cibran-o-mundo-do-motor | gl | 195 | 22.4 % | 20.4 % | — | — | — | — | sin validar | 0.0 % | 11.5 % | gl | 62.0 |  |
| cloplas-laverca | gl | 313 | 19.0 % | 19.3 % | 0.020 | 100.0 % | 100.0 % | 90.5 % | validada (75.1 %) | 0.0 % | 6.3 % | gl | 100.8 |  |
| fanny-alexander-lene | gl | 244 | 68.5 % | 68.0 % | — | — | — | — | sin validar | 0.0 % | 37.8 % | gl | 101.9 |  |
| mortos-en-vida-chapapote | gl | 162 | 54.2 % | 54.3 % | — | — | — | — | sin validar | 0.0 % | 41.4 % | gl | 58.1 |  |

## Peores casos

Mayor mediana de error de inicio:
- cloplas-laverca: 0.020 s
- pantis-un-aire: 0.020 s

Mayor WER:
- fanny-alexander-lene: 68.5 %
- mortos-en-vida-chapapote: 54.2 %
- pantis-un-aire: 34.1 %
- cibran-o-mundo-do-motor: 22.4 %
- cloplas-laverca: 19.0 %

## Notas

- Referencia semiautomática validada de oído en pantis-un-aire, cloplas-laverca: fiable a unos ±0,1 s, así que ahí manda el % ≤ 0,3 s más que la mediana. Solo cuentan las líneas marcadas «bien» (columna Referencia).
- Referencia sin validar de oído en cibran-o-mundo-do-motor, fanny-alexander-lene, mortos-en-vida-chapapote: no cuenta para la sincronía hasta que se valide.
- WER tolerante (gallego): no cuenta como error escribir de otra forma la misma palabra: gheada («janarme» / «ganarme»), seseo («corasón» / «corazón»), tildes y pronombres juntos o separados del verbo («deixei che» / «deixeiche»).
- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
