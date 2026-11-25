# 002 · Banco de sincronía por software

- **Fecha**: 19/11/2026
- **Estado**: aceptada
- **Afecta a**: reproductor

## Contexto

No hay instrumentación (ni interfaz de grabación ni fotodiodo) y el usuario decide quedarse con la
medida por software. Lo que sí se puede comprobar es que el código de reloj del reproductor
cumple las metas frente a una verdad conocida.

## Decisión

`kp-syncbench` simula, de forma determinista (semilla fija):

- la salida principal, con deriva de su cristal (±200 ppm), bloques, latencia y *jitter* de las
  marcas de tiempo;
- una segunda salida con su propio cristal, enganchada a la principal con *feed-forward* (los dos
  ritmos medidos por mínimos cuadrados) y un PI que recorta lo que quede;
- pantallas de 50, 60 y 144 Hz con su deriva y su latencia.

Metas, frente a la posición que de verdad suena por la salida principal:

- audio↔audio < 5 ms, sin saltos;
- el fotograma de vídeo mostrado contiene el audio que suena (0 ms fuera de su intervalo);
- la letra, dentro de un refresco de pantalla.

Resultados (`cargo run --release -p kp-syncbench`, 5–10 min simulados):

| Escenario | audio↔audio máx | A/V fuera del fotograma | letra máx |
|---|---|---|---|
| Una salida, TV 60 Hz y monitor 144 Hz | — | 0,29 ms | 0,30 ms |
| Dos salidas normales (+20/−80 ppm) | 0,23 ms | 0,29 ms | 0,30 ms |
| Dos salidas hostiles (+200/−200 ppm, *jitter* 1,5 ms) | 1,38 ms | 0,50 ms | 0,50 ms |

## Consecuencias

- El banco corre en la CI (`cargo test` lleva versiones de 60 s) y su binario se puede lanzar a mano.
- En el aparato real, `player --diagnose` informa de la deriva medida, de la latencia que declara
  cada dispositivo y de los instantes de presentación. Lo que no ve el software (DAC, panel) se
  ajusta con la calibración por salida.
