# 006 · El reproductor: referencia de tiempo, salidas, pantallas y tono

- **Fecha**: 19/11/2026
- **Estado**: aceptada (corrige un detalle de `00-vision.md` §6)
- **Afecta a**: reproductor

## Contexto

La visión decía «reloj maestro = el reloj hardware de la salida principal». Pero las órdenes del
servidor son anclas en el tiempo del servidor, y la salida principal puede desaparecer (se apaga
la tele) en mitad de una canción.

## Decisión

- **Referencia**: la línea de tiempo (`kp_core::Timeline`) va en el reloj monótono del equipo, con
  el desfase respecto al del servidor aprendido de la muestra de menor ida y vuelta.
- **Cada salida**, la principal incluida, la sigue con un `kp_clock::Follower`: mide su cristal
  contra ese reloj, compensa la relación de cristales (*feed-forward*) y un PI recorta el resto,
  remuestreando como mucho ±1000 ppm, que no se oye. Es el mismo código que pasa el banco
  (`decisiones/002`).
- **La salida principal** publica en el `MasterClock` lo que de verdad suena. Las pantallas siguen
  eso: la imagen y la letra van con el sonido que se oye, aunque la salida se retrase.
- **Hilo de audio**: no bloquea ni reserva memoria. La línea de tiempo se lee con `try_lock` (si
  falla, se usa la última posición); los mezcladores llegan ya construidos por canal y los viejos
  vuelven por otro para liberarse fuera.
- **Enrutado**: cada ruta lleva pista → salida, ganancia y retardo. Sin rutas, las dos pistas van a
  la salida por defecto. Calibración por id de dispositivo, en ms.
- **Pérdida de una salida**: se aplica su política (por defecto, pausa si es la principal y sigue
  si no) y se vuelve a abrir cuando vuelve. El estado lo dice con `master_lost`.
- **Pantallas**: winit y wgpu, con una ventana sin bordes a pantalla completa por monitor, y cada
  fotograma calculado para el instante en que se verá (siguiente vsync más la calibración de la
  pantalla). Un solo decodificador de vídeo, con hardware si puede, para todas. La letra usa la
  maquetación compartida (`kp-layout`, idéntica a Python y TS) con su relleno y su escena; el texto
  se dibuja con glyphon y las fuentes OFL de los temas, y el contorno con ocho pasadas.
- **Pantalla de espera**: siguiente canción, artista, quién canta y la descarga.
- **Al terminar** una canción se carga la siguiente en pausa: el operador da paso al siguiente
  cantante.
- **Tono**: Signalsmith Stretch siempre activo, también a 0 semitonos, para que su latencia (que el
  mezclador compensa leyendo por delante) no cambie; se aplica a la voz guía y a la música.

## Consecuencias

- Probado aquí sin aparato: banco de sincronía, maquetación contra los casos compartidos, tono
  (12 semitonos doblan la frecuencia) y extremo a extremo con dos salidas simuladas (deriva de
  60 ppm absorbida, desfase del sonido respecto a la línea de tiempo < 0,01 ms).
- El dibujo en pantalla solo se compila aquí (sin GPU ni pantalla); la CI construye los binarios
  de Windows y macOS, y la prueba real es `kp-player run --diagnose` en el equipo.
