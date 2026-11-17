# Banco · rev-blend · quick · con letra

- Fecha: 2026-11-16T14:16:59+01:00
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
| de | 5 | 0 | — | — | — | 0.024 | 0.037 | 99.7 % | 99.9 % | 0.063 | 0.018 | 96.8 % | — | 0 | 67 | 0.0 % | 11.7 % |
| en | 5 | 0 | — | — | — | 0.054 | 0.116 | 98.7 % | 99.0 % | 0.063 | 0.003 | 90.5 % | — | 0 | 66 | 0.1 % | 23.2 % |
| es | 5 | 0 | — | — | — | 0.025 | 0.033 | 99.8 % | 100.0 % | 0.095 | -0.001 | 98.5 % | — | 0 | 66 | 0.0 % | 18.0 % |
| fr | 5 | 0 | — | — | — | 0.029 | 0.037 | 99.8 % | 99.8 % | 0.092 | -0.015 | 92.3 % | — | 0 | 66 | 0.0 % | 15.2 % |
| total | 20 | 0 | — | — | — | 0.031 | 0.057 | 99.5 % | 99.7 % | 0.077 | 0.002 | 94.4 % | — | 0 | 66 | 0.0 % | 17.0 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 7.2 | 2867 | 2304 | 0.203 |
| aligner | 0.1 | 3335 | 5520 | 0.041 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | — | — | 0.053 | 100.0 % | 100.0 % | 93.9 % | manual | 0.3 % | 20.3 % | — | 49.0 |  |
| Wordsmith_-_The_Statement | en | 171 | — | — | 0.047 | 100.0 % | 100.0 % | 90.5 % | manual | 0.0 % | 24.1 % | — | 41.7 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | — | — | 0.069 | 98.9 % | 100.0 % | 93.6 % | manual | 0.0 % | 34.7 % | — | 55.9 |  |
| Ridgway_-_Fire_Inside | en | 284 | — | — | 0.046 | 93.2 % | 93.6 % | 77.0 % | manual | 0.0 % | 28.6 % | — | 68.8 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | — | — | 0.074 | 100.0 % | 100.0 % | 98.9 % | manual | 0.0 % | 8.5 % | — | 59.2 |  |
| 10._Disparan_-_criatura | es | 160 | — | — | 0.024 | 99.5 % | 100.0 % | 100.0 % | manual | 0.0 % | 18.0 % | — | 41.6 |  |
| Baila_-_Alfonso_Lugo | es | 210 | — | — | 0.019 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 23.6 % | — | 51.3 |  |
| Esencia_-_NandoMalo_ | es | 262 | — | — | 0.024 | 99.7 % | 100.0 % | 98.2 % | manual | 0.0 % | 13.5 % | — | 64.2 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | — | — | 0.029 | 99.8 % | 100.0 % | 98.3 % | manual | 0.0 % | 8.3 % | — | 47.8 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | — | — | 0.027 | 100.0 % | 100.0 % | 99.1 % | manual | 0.0 % | 26.4 % | — | 51.8 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | — | — | 0.048 | 100.0 % | 100.0 % | 97.8 % | manual | 0.0 % | 11.7 % | — | 57.9 |  |
| Der_Musiker_-_d-music | de | 271 | — | — | 0.020 | 99.1 % | 99.4 % | 98.0 % | manual | 0.0 % | 11.3 % | — | 66.8 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | — | — | 0.055 | 98.9 % | 100.0 % | 94.6 % | manual | 0.0 % | 17.2 % | — | 59.9 |  |
| Keine_Lust_-_Jonny_M | de | 229 | — | — | 0.016 | 100.0 % | 100.0 % | 95.8 % | manual | 0.0 % | 1.5 % | — | 56.9 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | — | — | 0.029 | 100.0 % | 100.0 % | 96.0 % | manual | 0.0 % | 16.6 % | — | 57.3 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | — | — | 0.024 | 100.0 % | 100.0 % | 97.6 % | manual | 0.0 % | 8.5 % | — | 48.6 |  |
| Confession_-_Quesabe | fr | 148 | — | — | 0.030 | 99.3 % | 99.3 % | 87.2 % | manual | 0.2 % | 20.1 % | — | 35.9 |  |
| Mère_nature_-_Law' | fr | 225 | — | — | 0.036 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 6.7 % | — | 55.2 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | — | — | 0.031 | 100.0 % | 100.0 % | 88.1 % | manual | 0.0 % | 32.3 % | — | 49.5 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | — | — | 0.020 | 100.0 % | 100.0 % | 94.1 % | manual | 0.0 % | 8.3 % | — | 45.5 |  |

## Peores casos

Mayor mediana de error de inicio:
- Cortez_-_Feel__Stripped_: 0.074 s
- The_Rinn_-_Voices__2017_Version_: 0.069 s
- Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: 0.055 s
- Kinematic_-_Peyote: 0.053 s
- 1_Freak_-_Automatisch_Gekommen: 0.048 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
