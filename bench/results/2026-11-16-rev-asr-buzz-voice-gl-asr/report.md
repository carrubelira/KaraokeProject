# Banco · rev-asr-buzz-voice · gl · sin letra

- Fecha: 2026-11-16T23:53:47+01:00
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

Mel-Band RoFormer (Kim, 8 s) + BuzzASR Galician Whisper large-v3 reading each stretch of singing on its own + line segmenter + lyrics aligner

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v5 {'model': 'buzz-large-v3-gl', 'by_voice': True}
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v14 {'second': '', 'rest_penalty': 0.0}

## Resumen

| Grupo | Canciones | Fallos | WER | WER tolerante | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gl | 5 | 0 | 32.7 % | 31.4 % | 17.0 % | 0.020 | 0.045 | 99.3 % | 99.3 % | 0.020 | 0.041 | 87.8 % | — | 0 | 90 | 0.0 % | 19.4 % |
| total | 5 | 0 | 32.7 % | 31.4 % | 17.0 % | 0.020 | 0.045 | 99.3 % | 99.3 % | 0.020 | 0.041 | 87.8 % | — | 0 | 90 | 0.0 % | 19.4 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 8.2 | 2867 | 2372 | 0.205 |
| transcriber | 3.6 | 3319 | 2000 | 0.103 |
| segmenter | — | 0 | 77 | 0.000 |
| aligner | 0.1 | 1555 | 2738 | 0.017 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pantis-un-aire | gl | 287 | 29.4 % | 27.2 % | 0.020 | 100.0 % | 100.0 % | 84.7 % | validada (75.7 %) | 0.0 % | 12.8 % | gl | 124.6 |  |
| cibran-o-mundo-do-motor | gl | 195 | 15.8 % | 13.8 % | — | — | — | — | sin validar | 0.0 % | 5.9 % | gl | 55.7 |  |
| cloplas-laverca | gl | 313 | 15.3 % | 15.8 % | 0.020 | 98.5 % | 98.5 % | 91.5 % | validada (75.1 %) | 0.0 % | 5.1 % | gl | 101.5 |  |
| fanny-alexander-lene | gl | 244 | 65.2 % | 66.9 % | — | — | — | — | sin validar | 0.0 % | 36.2 % | gl | 79.2 |  |
| mortos-en-vida-chapapote | gl | 162 | 53.9 % | 50.9 % | — | — | — | — | sin validar | 0.0 % | 37.0 % | gl | 52.6 |  |

## Peores casos

Mayor mediana de error de inicio:
- cloplas-laverca: 0.020 s
- pantis-un-aire: 0.020 s

Mayor WER:
- fanny-alexander-lene: 65.2 %
- mortos-en-vida-chapapote: 53.9 %
- pantis-un-aire: 29.4 %
- cibran-o-mundo-do-motor: 15.8 %
- cloplas-laverca: 15.3 %

## Notas

- Referencia semiautomática validada de oído en pantis-un-aire, cloplas-laverca: fiable a unos ±0,1 s, así que ahí manda el % ≤ 0,3 s más que la mediana. Solo cuentan las líneas marcadas «bien» (columna Referencia).
- Referencia sin validar de oído en cibran-o-mundo-do-motor, fanny-alexander-lene, mortos-en-vida-chapapote: no cuenta para la sincronía hasta que se valide.
- WER tolerante (gallego): no cuenta como error escribir de otra forma la misma palabra: gheada («janarme» / «ganarme»), seseo («corasón» / «corazón»), tildes y pronombres juntos o separados del verbo («deixei che» / «deixeiche»).
- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
