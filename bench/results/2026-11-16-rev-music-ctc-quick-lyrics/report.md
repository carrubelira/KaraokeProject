# Banco · rev-music-ctc · quick · con letra

- Fecha: 2026-11-16T13:40:05+01:00
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

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 5 | 0 | — | — | 0.029 | 0.050 | 99.7 % | 99.8 % | 0.104 | 0.021 | 96.4 % | — | 0 | 74 | 0.0 % | 22.3 % |
| en | 5 | 0 | — | — | 0.050 | 0.160 | 98.5 % | 98.8 % | 0.114 | 0.034 | 90.1 % | — | 0 | 73 | 0.1 % | 25.6 % |
| es | 5 | 0 | — | — | 0.025 | 0.033 | 99.9 % | 100.0 % | 0.138 | 0.005 | 98.5 % | — | 0 | 73 | 0.0 % | 27.1 % |
| fr | 5 | 0 | — | — | 0.024 | 0.038 | 99.6 % | 99.8 % | 0.122 | -0.009 | 91.3 % | — | 0 | 73 | 0.1 % | 24.2 % |
| total | 20 | 0 | — | — | 0.030 | 0.072 | 99.4 % | 99.6 % | 0.119 | 0.014 | 94.0 % | — | 0 | 73 | 0.0 % | 24.8 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 6.2 | 2867 | 2309 | 0.204 |
| aligner | 10.7 | 2133 | 4264 | 0.031 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | — | 0.056 | 99.3 % | 99.3 % | 93.9 % | manual | 0.4 % | 21.7 % | — | 42.7 |  |
| Wordsmith_-_The_Statement | en | 171 | — | 0.036 | 100.0 % | 100.0 % | 90.7 % | manual | 0.0 % | 22.7 % | — | 39.9 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | — | 0.075 | 98.4 % | 99.5 % | 95.1 % | manual | 0.0 % | 35.7 % | — | 53.6 |  |
| Ridgway_-_Fire_Inside | en | 284 | — | 0.045 | 93.3 % | 93.3 % | 73.4 % | manual | 0.0 % | 40.7 % | — | 66.0 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | — | 0.077 | 99.1 % | 100.0 % | 98.9 % | manual | 0.0 % | 7.3 % | — | 56.7 |  |
| 10._Disparan_-_criatura | es | 160 | — | 0.025 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 34.0 % | — | 37.0 |  |
| Baila_-_Alfonso_Lugo | es | 210 | — | 0.024 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 35.9 % | — | 49.3 |  |
| Esencia_-_NandoMalo_ | es | 262 | — | 0.021 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 22.2 % | — | 61.7 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | — | 0.028 | 99.8 % | 100.0 % | 98.3 % | manual | 0.0 % | 6.6 % | — | 46.1 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | — | 0.032 | 100.0 % | 100.0 % | 99.1 % | manual | 0.0 % | 36.8 % | — | 49.6 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | — | 0.058 | 100.0 % | 100.0 % | 97.8 % | manual | 0.0 % | 19.9 % | — | 45.9 |  |
| Der_Musiker_-_d-music | de | 271 | — | 0.021 | 99.4 % | 99.4 % | 96.3 % | manual | 0.0 % | 16.7 % | — | 64.3 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | — | 0.078 | 98.9 % | 100.0 % | 94.6 % | manual | 0.0 % | 29.0 % | — | 57.8 |  |
| Keine_Lust_-_Jonny_M | de | 229 | — | 0.019 | 99.8 % | 99.8 % | 95.8 % | manual | 0.0 % | 4.8 % | — | 54.7 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | — | 0.038 | 100.0 % | 100.0 % | 96.0 % | manual | 0.0 % | 41.1 % | — | 54.9 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | — | 0.023 | 99.6 % | 100.0 % | 97.6 % | manual | 0.1 % | 41.9 % | — | 44.0 |  |
| Confession_-_Quesabe | fr | 148 | — | 0.027 | 98.6 % | 98.9 % | 83.3 % | manual | 0.2 % | 16.6 % | — | 34.5 |  |
| Mère_nature_-_Law' | fr | 225 | — | 0.025 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 6.3 % | — | 53.1 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | — | 0.026 | 100.0 % | 100.0 % | 88.1 % | manual | 0.0 % | 32.2 % | — | 47.6 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | — | 0.020 | 100.0 % | 100.0 % | 94.1 % | manual | 0.0 % | 24.2 % | — | 43.7 |  |

## Peores casos

Mayor mediana de error de inicio:
- Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: 0.078 s
- Cortez_-_Feel__Stripped_: 0.077 s
- The_Rinn_-_Voices__2017_Version_: 0.075 s
- 1_Freak_-_Automatisch_Gekommen: 0.058 s
- Kinematic_-_Peyote: 0.056 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
