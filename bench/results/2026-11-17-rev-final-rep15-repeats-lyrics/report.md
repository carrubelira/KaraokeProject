# Banco · rev-final-rep15 · repeats · con letra

- Fecha: 2026-11-17T10:47:40+01:00
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

Mel-Band RoFormer (Kim, 8 s) + Whisper + lyrics aligner (the music model at 0.3, resting 0.05, singing a stanza's lines again costs 15)

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v6
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v15 {'second': 'music-w2vbert-ctc', 'second_weight': 0.3, 'rest_penalty': 0.05, 'repeat_penalty': 15.0}

## Resumen

| Grupo | Canciones | Fallos | WER | WER tolerante | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| repeats-marked | 1 | 0 | — | — | — | 0.046 | 0.209 | 94.4 % | 94.4 % | 0.060 | 0.148 | 82.3 % | — | 0 | 89 | 0.0 % | 21.3 % |
| repeats-unmarked | 7 | 0 | — | — | — | 0.039 | 0.634 | 93.2 % | 93.5 % | 0.078 | -0.275 | 86.0 % | — | 0 | 69 | 0.0 % | 17.2 % |
| total | 8 | 0 | — | — | — | 0.040 | 0.600 | 93.3 % | 93.6 % | 0.077 | -0.241 | 85.7 % | — | 0 | 70 | 0.0 % | 17.7 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 6.9 | 2867 | 2388 | 0.206 |
| aligner | 0.1 | 2133 | 3824 | 0.055 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| marked-Quentin_Hannappe_-_Keep_On | en | 190 | — | — | 0.046 | 94.4 % | 94.4 % | 82.3 % | manual | 0.0 % | 21.3 % | — | 65.0 |  |
| unmarked-Guayeteo_-_JhoyKing | es | 158 | — | — | 0.031 | 89.8 % | 90.2 % | 77.9 % | manual | 0.0 % | 20.2 % | — | 42.5 |  |
| unmarked-LUNABLIND_-_Vision__Radio_Edit_ | en | 221 | — | — | 0.065 | 96.4 % | 96.4 % | 96.2 % | manual | 0.0 % | 10.9 % | — | 57.3 |  |
| unmarked-Libre_by_CybeR_AttaCK_-_CyberAttacK | fr | 217 | — | — | 0.028 | 95.8 % | 96.7 % | 84.1 % | manual | 0.0 % | 36.4 % | — | 57.2 |  |
| unmarked-Lower_Loveday_-_Is_It_Right_ | en | 180 | — | — | 0.067 | 90.6 % | 90.6 % | 85.4 % | manual | 0.0 % | 16.6 % | — | 46.7 |  |
| unmarked-Palabras_-_Javier_Gomez_Bello | es | 216 | — | — | 0.030 | 100.0 % | 100.0 % | 96.2 % | manual | 0.0 % | 3.4 % | — | 55.4 |  |
| unmarked-Quentin_Hannappe_-_Keep_On | en | 190 | — | — | 0.052 | 85.3 % | 85.3 % | 77.7 % | manual | 0.0 % | 19.7 % | — | 49.1 |  |
| unmarked-de_bonne_humeur_-_Le_Nez_Tordu | fr | 161 | — | — | 0.034 | 90.4 % | 90.8 % | 86.1 % | manual | 0.0 % | 13.0 % | — | 42.4 |  |

## Peores casos

Mayor mediana de error de inicio:
- unmarked-Lower_Loveday_-_Is_It_Right_: 0.067 s
- unmarked-LUNABLIND_-_Vision__Radio_Edit_: 0.065 s
- unmarked-Quentin_Hannappe_-_Keep_On: 0.052 s
- marked-Quentin_Hannappe_-_Keep_On: 0.046 s
- unmarked-de_bonne_humeur_-_Le_Nez_Tordu: 0.034 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
