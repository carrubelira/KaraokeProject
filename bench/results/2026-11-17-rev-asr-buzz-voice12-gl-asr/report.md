# Banco · rev-asr-buzz-voice12 · gl · sin letra

- Fecha: 2026-11-17T01:04:15+01:00
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

Mel-Band RoFormer (Kim, 8 s) + BuzzASR Galician Whisper large-v3 reading stretches of singing of at most 12 s + line segmenter + lyrics aligner

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v5 {'model': 'buzz-large-v3-gl', 'by_voice': True, 'stretch_seconds': 12.0}
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v14 {'second': '', 'rest_penalty': 0.0}

## Resumen

| Grupo | Canciones | Fallos | WER | WER tolerante | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gl | 5 | 0 | 31.8 % | 30.3 % | 15.9 % | 0.020 | 0.042 | 99.5 % | 99.5 % | 0.020 | 0.038 | 87.5 % | — | 0 | 94 | 0.0 % | 19.6 % |
| total | 5 | 0 | 31.8 % | 30.3 % | 15.9 % | 0.020 | 0.042 | 99.5 % | 99.5 % | 0.020 | 0.038 | 87.5 % | — | 0 | 94 | 0.0 % | 19.6 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 8.2 | 2867 | 2372 | 0.205 |
| transcriber | 3.2 | 3287 | 1997 | 0.120 |
| segmenter | — | 0 | 76 | 0.000 |
| aligner | 0.1 | 1555 | 2735 | 0.017 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pantis-un-aire | gl | 287 | 24.1 % | 21.6 % | 0.020 | 100.0 % | 100.0 % | 85.6 % | validada (75.7 %) | 0.0 % | 13.8 % | gl | 102.1 |  |
| cibran-o-mundo-do-motor | gl | 195 | 17.8 % | 15.8 % | — | — | — | — | sin validar | 0.0 % | 7.4 % | gl | 62.8 |  |
| cloplas-laverca | gl | 313 | 17.2 % | 17.7 % | 0.020 | 98.8 % | 98.8 % | 89.8 % | validada (75.1 %) | 0.0 % | 7.1 % | gl | 125.8 |  |
| fanny-alexander-lene | gl | 244 | 64.6 % | 65.1 % | — | — | — | — | sin validar | 0.0 % | 34.1 % | gl | 95.4 |  |
| mortos-en-vida-chapapote | gl | 162 | 53.5 % | 50.9 % | — | — | — | — | sin validar | 0.0 % | 35.8 % | gl | 55.3 |  |

## Peores casos

Mayor mediana de error de inicio:
- cloplas-laverca: 0.020 s
- pantis-un-aire: 0.020 s

Mayor WER:
- fanny-alexander-lene: 64.6 %
- mortos-en-vida-chapapote: 53.5 %
- pantis-un-aire: 24.1 %
- cibran-o-mundo-do-motor: 17.8 %
- cloplas-laverca: 17.2 %

## Notas

- Referencia semiautomática validada de oído en pantis-un-aire, cloplas-laverca: fiable a unos ±0,1 s, así que ahí manda el % ≤ 0,3 s más que la mediana. Solo cuentan las líneas marcadas «bien» (columna Referencia).
- Referencia sin validar de oído en cibran-o-mundo-do-motor, fanny-alexander-lene, mortos-en-vida-chapapote: no cuenta para la sincronía hasta que se valide.
- WER tolerante (gallego): no cuenta como error escribir de otra forma la misma palabra: gheada («janarme» / «ganarme»), seseo («corasón» / «corazón»), tildes y pronombres juntos o separados del verbo («deixei che» / «deixeiche»).
- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
