# 009 · El globo de noche, con Galicia en su contexto real

- **Fecha**: 20/11/2026
- **Estado**: sustituida por `010` (el control ya no tiene globo)
- **Afecta a**: web (inicio)

## Contexto

El usuario mantiene el globo de inicio de noche, pero pide más realismo: que Galicia deje de ser
la única tierra de un planeta pequeño.

## Decisión

- `scripts/galicia_map.py` cubre todo el noroeste de la Península (`BOX`, de −12,5° a −2,8° de
  longitud y de 39,4° a 45,8° de latitud). Toda la tierra que asoma sobre el mar (Galicia, el
  norte de Portugal, Asturias, León, Zamora) sale del relieve en sus proporciones reales. Galicia
  ocupa ±22° del planeta (antes ±34°), así que se ve el océano y la curva del mundo.
- Rejilla de 1024 × 1024 (unos 0,75 km por celda); el archivo pesa 426 kB comprimido.
- La capa de provincias marca con 5 la tierra de alrededor. El atlas la anota (96/255) y el
  shader la pinta en penumbra (32 % de luz, costa más tenue), con la frontera de Galicia
  dibujada.
- Luces: Kontur de España y de Portugal. Galicia, a toda luz; fuera, al 40 % y su resplandor al
  30 %. Galicia queda encendida y el resto, a oscuras.
- Nombres en la oscuridad: Océano Atlántico, Cantábrico, Portugal, Asturias, León y Zamora.
- El `body` del control es transparente: el lienzo del globo va debajo de la página.

## Consecuencias

- Créditos en `NOTICE.md` (Kontur de Portugal, Natural Earth de los vecinos, el fondo del mar de
  ETOPO1).
