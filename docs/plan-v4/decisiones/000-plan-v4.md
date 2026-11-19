# 000 · El plan v4 sustituye al plan v3

- **Fecha**: 19/11/2026
- **Estado**: aceptada
- **Afecta a**: todas las áreas

## Contexto

v3 es un único `karaoke-server` en WSL que lanza `karaoke make` en un *scope* de systemd sobre una
GPU de 4 GB, y una PWA que reproduce con Web Audio. Hace falta sincronía precisa en un reproductor
con dos pantallas y una o dos salidas de audio, y procesado nativo en Windows y Linux.

## Decisión

Se adopta una arquitectura distribuida: servidor (fuente de verdad, CAS, cola), workers *pull* con
GPU, reproductor nativo en Rust y una interfaz de control web pensada para teclado. Manda
`docs/plan-v4/00-vision.md`. Sin retrocompatibilidad con v3 en tiempo de ejecución; solo se ofrece
un migrador de paquetes.

Decisiones tomadas en la revisión: micrófonos fuera del sistema; servidor, worker y reproductor
pueden ser el mismo PC; el tono se mantiene en el reproductor (signalsmith-stretch); el editor
conserva un mini reproductor web; pistas en Opus/Ogg con la sonoridad como metadato; token por nodo
y TLS siempre; política de desconexión por salida; control con paleta de comandos y atajos.

## Consecuencias

- `docs/plan-v3/` pasa a ser historia; sus decisiones solo obligan si `00-vision.md` las cita.
- Se eliminan la PWA, el reproductor web (salvo el del editor), el modo fiesta y las zonas de red.
- El despliegue deja de depender de WSL.

---

Plantilla para nuevas decisiones (`NNN-titulo-corto.md`): Fecha · Estado (propuesta, aceptada,
sustituida por NNN) · Afecta a · Contexto · Decisión · Consecuencias. Cortas: media página.
