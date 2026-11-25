# 007 · La interfaz de control: un registro de órdenes y UI optimista

- **Fecha**: 20/11/2026
- **Estado**: aceptada
- **Afecta a**: web

## Decisión

- **Reescrita** en el mismo SvelteKit. Desaparecen la PWA, el reproductor web, la fiesta, el
  emparejado, el cliente v3 y el servidor simulado; se conservan la letra (`lib/lyrics`), el
  editor (`lib/editor`), el motor de audio del navegador (solo para el editor), el globo y el
  sistema visual. Los estilos del control llevan prefijo `ctl-`, para no pisar los del componente
  de letra.
- **Un registro de órdenes** (`lib/commands/registry.svelte.ts`): id, título, grupo, ámbito,
  atajos y `run`. De él salen la paleta (`Mod+K`, búsqueda difusa sobre órdenes y entidades), los
  atajos (acordes y secuencias como `g b`), la chuleta (`?`) y la página de atajos. Las órdenes con
  ámbito (`library`, `queue`, `playlist`, `outputs`, `editor`) ganan a las globales mientras su
  sección está activa. Las órdenes que se ejecutan escribiendo en un campo solo cuentan si llevan
  modificador.
- **Preferencias en el servidor** (atajos, tema, densidad, tamaños de paneles, reproductor y
  lista): siguen al operador a otro ordenador.
- **UI optimista**: el cambio se pinta al momento y se revierte con aviso si el servidor lo
  rechaza; una lista que choca con una versión más nueva se rehace encima de ella. La entrada de
  deshacer se apila en el mismo instante (la tecla siguiente puede ser `Mod+Z`).
- **Medida**: el e2e cronometra dentro de la página, de la pulsación al cambio en el DOM (meta
  < 100 ms), y pasa axe (WCAG 2 A/AA) en cada sección.

## Consecuencias

- El e2e del control corre contra el servidor real con un worker falso (`e2e/control/serve.py`),
  sin servidor simulado que mantener.
