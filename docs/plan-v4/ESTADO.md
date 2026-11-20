# Plan v4 · Estado

Tablero por fases (`00-vision.md` §9). Cada fase actualiza **su fila** tras cada hito.

| Fase | Entrega | Estado | Rama | Último hito |
|---|---|---|---|---|
| 0a | Motor del reproductor | hecho | `claude/trusting-johnson-3p992a` | pipeline propio (`decisiones/001`); `kp-clock`, `kp-mix` |
| 0b | Banco de sincronía por software | hecho | `claude/trusting-johnson-3p992a` | `kp-syncbench`: audio↔audio 1,4 ms máx en el peor caso (`decisiones/002`) |
| 1 | Contratos v2 y migrador v3 → manifiesto | hecho | `claude/trusting-johnson-3p992a` | manifiesto, letra, nodos, órdenes y enrutado; Opus con `gain_db`; `karaoke package`; `kp-proto` (`decisiones/003`) |
| 2 | Servidor: CAS, cola con lease, enrolado y TLS, API/WS | hecho | `claude/trusting-johnson-3p992a` | servidor v4 reescrito: CAS, subidas reanudables, DAG con *lease* y afinidad, nodos, operadores, listas y reproductores (`decisiones/004`) |
| 3 | Worker en Windows y Linux, tarea `make` gruesa | hecho | `claude/trusting-johnson-3p992a` | `karaoke-worker`: *pull*, fetch, make y render, Job Objects/systemd, TLS fijado (`decisiones/005`) |
| 3.5 | Corte vertical: reproductor mínimo | hecho | `claude/trusting-johnson-3p992a` | `make e2e-v4`: subida → worker → lista → caché → reproducción |
| 4 | Control: comandos, paleta, atajos, paneles, cola | hecho | `claude/trusting-johnson-3p992a` | registro de órdenes, paleta, chuleta, atajos reasignables, paneles, UI optimista con deshacer; e2e solo con teclado < 100 ms y axe (`decisiones/007`) |
| 5 | Reproductor: 1 pantalla y 1 salida completas, con tono | hecho (falta probarlo en el equipo) | `claude/trusting-johnson-3p992a` | `kp-player`: caché verificada, órdenes con ancla, pantalla de espera, letra con `kp-layout`, tono con Signalsmith (`decisiones/006`) |
| 6 | Reproductor: 2 pantallas, 2.ª salida, enrutado, calibración | hecho (falta probarlo en el equipo) | `claude/trusting-johnson-3p992a` | una ventana por monitor, `Follower` por salida, matriz de enrutado, calibración y altas y bajas en caliente |
| 7 | Editor con mini reproductor y MP4 | hecho | `claude/trusting-johnson-3p992a` | editor v2 con teclado, versiones de manifiesto, MP4 como tarea `render` (`decisiones/008`) |
| 8 | (opcional) Varios reproductores | fuera hasta que haga falta | — | — |

## Decidido después

- Medición solo por software; reproductor en Windows con NVIDIA y macOS; el tono también se
  aplica a la voz guía; el globo de inicio se mantiene de noche, con Galicia en su contexto real.
