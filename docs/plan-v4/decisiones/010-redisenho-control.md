# 010 · Rediseño del control: tradicional, sobrio y coherente

- **Fecha**: 22/11/2026
- **Estado**: aceptada (sustituye a `009` y a la parte visual de `007`)
- **Afecta a**: web (todas las vistas del control)

## Contexto

El usuario encuentra el control feo y confuso: las partículas del globo no aportan nada, cada
vista tiene su propio diseño, la de trabajos cuesta entenderla (habla de *tasks*, *leases* y
*kinds*), las fuentes parecen las de cualquier demo y hay etiquetas de jerga («En liña»,
«Players», «Workers»). Pide una interfaz tradicional; el guiño a Galicia puede quedar, sin globo
y en segundo plano.

## Decisión

- **Tema oscuro sobrio**, un único juego de *tokens* (`web/src/lib/ui/styles/tokens.css`): fondo
  gris pizarra `#1b1e22`, superficies `#23272c`/`#2b3036`, bordes `#3a4047`, tres niveles de texto
  que cumplen AA, un solo acento azul atlántico (`#4c8dc9`, `#2f6ea8` en el botón principal) y
  verde, ámbar y rojo solo en indicadores pequeños. Radio de 6 px, sin degradados, sombras
  grandes ni desenfoques. Los nombres antiguos (`--ceo`, `--texto`…) quedan como alias para la
  letra y el editor.
- **IBM Plex Sans y Plex Mono** (OFL), autoalojadas y recortadas al latín con
  `scripts/build_web_fonts.py`; mono solo para tiempos, cifras y atajos.
- **Barra lateral fija** con tres grupos (Sesión: Directo; Contido: Biblioteca, Crear; Sistema:
  Traballos, Equipos, Saídas, Axustes), iconos de trazo propios, el atajo de cada sección y,
  abajo, la conexión con el servidor y el operador.
- **Un solo kit** (`control.css`, prefijo `ctl-`): cabecera de página, panel con cabecera, tabla
  de verdad (`<table>`, filas de 2,4 rem, cifras en mono a la derecha, cursor con borde de
  acento), botones, campos, insignias de estado con punto y palabra, barra de progreso, estado
  vacío, barra de herramientas y filtros segmentados. Cajón lateral (`Drawer`) y diálogo
  (`Dialog`) comunes. Todas las vistas, el editor incluido, se montan con esas piezas.
- **Traballos en lenguaje claro**: `lib/control/describe.ts` traduce cada trabajo a un estado
  (Na cola, Procesando, En pausa, Feito, Fallou, Cancelado) y a un paso («Separando a voz»,
  «Agardando un equipo libre»…), con progreso, equipo, tiempo restante y hora. Filtros Todos /
  En curso / Fallidos / Feitos (`f`); `Enter` abre el detalle con los pasos como línea de tiempo,
  el error completo y las acciones.
- **Equipos** (antes «Workers», ruta `/equipos`): dos tablas, equipos de proceso y reproductores,
  y un diálogo «Engadir equipo» con la orden lista para copiar.
- **Directo** en dos columnas fijas (lista; Agora y A seguir). Se retiran los paneles
  redimensionables, las disposiciones `Ctrl+1/2` y el tema claro.
- **Inicio**: cuatro tarjetas (agora soa, seguinte, traballos, equipos) y los últimos trabajos.
- **Galicia**: el contorno real (Natural Earth) como línea de 1 px casi transparente en la barra
  lateral y, mayor, en la pantalla de entrada. `scripts/galicia_map.py` solo genera ese contorno
  (`web/src/lib/shell/galicia.ts`); el globo, sus datos y su motor WebGL se borran.
- Textos sin jerga en gl, es y en; la barra de estado ya no muestra el tiempo de cada orden (lo
  sigue midiendo el e2e).

## Consecuencias

- Menos código y ningún WebGL en el control; el inicio carga al momento.
- Una vista nueva se hace con las mismas clases y queda igual que las demás.
- Se pierde el globo de noche (`009`) y sus créditos de datos (Kontur, Mapzen, Wikidata).
- Arreglado de paso: el atajo `+` (subir volumen, dar prioridad) no se reconocía ni se pintaba.
