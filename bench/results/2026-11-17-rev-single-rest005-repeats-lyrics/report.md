# Banco · rev-single-rest005 · repeats · con letra

- Fecha: 2026-11-17T10:42:14+01:00
- Commit: a85e232-dirty
- Banco 3.0.0, normalización v1
- Referencias: en manual, es manual, fr manual

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

Mel-Band RoFormer (Kim, 8 s) + Whisper + lyrics aligner (each language's model alone, resting costs 0.05 (to tell the two changes apart on repeats))

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v6
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v15 {'second': '', 'rest_penalty': 0.05}

## Resumen

| Grupo | Canciones | Fallos | WER | WER tolerante | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| repeats-marked | 1 | 0 | — | — | — | 0.044 | 0.049 | 100.0 % | 100.0 % | 0.050 | 0.045 | 96.0 % | — | 0 | 81 | 0.0 % | 20.7 % |
| repeats-unmarked | 7 | 0 | — | — | — | 0.036 | 0.056 | 99.4 % | 99.6 % | 0.071 | 0.017 | 93.3 % | — | 0 | 60 | 0.0 % | 19.1 % |
| total | 8 | 0 | — | — | — | 0.037 | 0.055 | 99.5 % | 99.6 % | 0.067 | 0.020 | 93.5 % | — | 0 | 60 | 0.0 % | 19.3 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 6.9 | 2867 | 2388 | 0.206 |
| aligner | 0.1 | 1559 | 3678 | 0.016 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| marked-Quentin_Hannappe_-_Keep_On | en | 190 | — | — | 0.044 | 100.0 % | 100.0 % | 96.0 % | manual | 0.0 % | 20.7 % | — | 58.4 |  |
| unmarked-Guayeteo_-_JhoyKing | es | 158 | — | — | 0.026 | 98.9 % | 99.2 % | 77.9 % | manual | 0.0 % | 25.9 % | — | 36.7 |  |
| unmarked-LUNABLIND_-_Vision__Radio_Edit_ | en | 221 | — | — | 0.062 | 99.3 % | 99.3 % | 97.6 % | manual | 0.0 % | 13.1 % | — | 49.1 |  |
| unmarked-Libre_by_CybeR_AttaCK_-_CyberAttacK | fr | 217 | — | — | 0.029 | 99.7 % | 100.0 % | 96.5 % | manual | 0.0 % | 33.6 % | — | 49.8 |  |
| unmarked-Lower_Loveday_-_Is_It_Right_ | en | 180 | — | — | 0.056 | 99.5 % | 99.5 % | 96.7 % | manual | 0.0 % | 16.5 % | — | 39.7 |  |
| unmarked-Palabras_-_Javier_Gomez_Bello | es | 216 | — | — | 0.030 | 100.0 % | 100.0 % | 99.5 % | manual | 0.0 % | 8.5 % | — | 47.5 |  |
| unmarked-Quentin_Hannappe_-_Keep_On | en | 190 | — | — | 0.046 | 98.8 % | 98.8 % | 91.4 % | manual | 0.0 % | 18.7 % | — | 41.9 |  |
| unmarked-de_bonne_humeur_-_Le_Nez_Tordu | fr | 161 | — | — | 0.030 | 99.6 % | 100.0 % | 97.0 % | manual | 0.0 % | 17.5 % | — | 35.9 |  |

## Peores casos

Mayor mediana de error de inicio:
- unmarked-LUNABLIND_-_Vision__Radio_Edit_: 0.062 s
- unmarked-Lower_Loveday_-_Is_It_Right_: 0.056 s
- unmarked-Quentin_Hannappe_-_Keep_On: 0.046 s
- marked-Quentin_Hannappe_-_Keep_On: 0.044 s
- unmarked-Palabras_-_Javier_Gomez_Bello: 0.030 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
