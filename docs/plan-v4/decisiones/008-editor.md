# 008 · El editor de letra y tiempos en v4

- **Fecha**: 20/11/2026
- **Estado**: aceptada
- **Afecta a**: web, servidor

## Decisión

- El editor lee la letra (`GET /api/contents/{id}/lyrics`) y el manifiesto de la versión actual,
  la convierte en el documento de v3 para reutilizar sus operaciones (`lib/editor/ops.ts`, con sus
  tests) y la forma de onda, y guarda con `PUT /api/contents/{id}/lyrics` indicando la versión de
  la que partió: se crea una versión nueva del manifiesto y solo es nuevo el blob de la letra. Si
  la canción cambió mientras tanto, se rechaza (409) y se avisa.
- Suena en el navegador (el «mini reproductor»): las pistas Opus salen directamente del almacén
  (`/api/blobs/{sha}`).
- Todo con teclado (ámbito `editor`): `Espacio` escucha la línea, `l` la repite, `t` la cronometra
  a toques, `j`/`k` cambian de línea, `←`/`→` de palabra, `,`/`.` mueven la línea 50 ms,
  `Mayús`/`Alt` + `,`/`.` mueven el inicio o el final de la palabra, `Enter` corrige el texto, `u`
  salta a la siguiente palabra dudosa, `Mod+Z` deshace dentro del editor y `Mod+S` guarda.
- El MP4 es una tarea `render` del worker (`decisiones/005`), que se lanza desde la Biblioteca (`m`).
