# GitHub Projects: acceso y automatización

Repositorio: `fer-trk/project-ai-computer-vision-objects`.

## Estado comprobado

La CLI reconoce la cuenta `fer-trk`. En la comprobación del 20 de octubre de 2026 sus permisos eran `gist`, `read:org`, `repo`, `workflow`; faltaba `project`. La consulta al tablero no pudo completarse. Esto no significa que no exista un Project.

No hace falta una sincronización especial de la conversación con el tablero: con la CLI autorizada se pueden crear issues, incorporarlas al Project y consultar/actualizar tarjetas desde este entorno. El conector GitHub disponible no expone aquí herramientas específicas de Projects; para el tablero se utilizará `gh`.

## Autorización local (completada)

En una terminal de tu equipo:

```powershell
gh auth refresh --hostname github.com --scopes project
gh auth status
gh project list --owner fer-trk
```

Completar la autorización en el navegador con tu cuenta. Si la sesión realmente caduca, usar `gh auth login --hostname github.com --web --scopes project`. No compartir tokens en el chat ni guardarlos en el repositorio.

Después, facilitar el enlace al Project existente o indicar que hay que crear uno. Revisar primero las tarjetas existentes. Crear issues reales en el repositorio, no solo notas borrador, para poder enlazar PR y cierre. Identificar por T01–T14 y URL antes de añadir para evitar duplicados.

Ejemplo ilustrativo (reemplazar número y URL por valores reales):

```powershell
gh project item-add NUMERO --owner fer-trk --url URL_DE_LA_ISSUE
```

Actualización: autorización project completada y Project creado: https://github.com/users/fer-trk/projects/1. Catorce issues vinculadas, campos Nivel y Orden y vistas Kanban configuradas. Todas las tarjetas comienzan en Pendiente. Las automatizaciones de Actions aún no están configuradas; no hay secret del Project instalado por este trabajo.

## Automatización propuesta

1. Vincular el Project al repositorio y configurar estados de `plan.md`.
2. Usar automatizaciones nativas del Project cuando cubran el comportamiento deseado.
3. Completar con Actions solo lo necesario: incorporar issues y mover la issue vinculada a revisión al abrir un PR listo para revisar. El cuerpo del PR debe vincular inequívocamente la issue.
4. El usuario decide pasar a Preparado e iniciar una tarea. No mover tarjetas a En curso simplemente por crear una rama.
5. Tras revisión humana y merge, cerrar la issue vinculada y moverla a Hecho. Un PR cerrado sin integrar no completa la tarea; una issue reabierta debe volver a Pendiente.

Autorización local y credenciales de Actions son independientes. El `GITHUB_TOKEN` del repositorio no basta para modificar Projects: un workflow necesita una credencial con acceso al Project, guardada como secret de Actions, con alcance mínimo compatible y caducidad. No extraer ni reutilizar silenciosamente la credencial local.

Diseñar el workflow antes de pedir configurar el secret. No ejecutar código de PR no confiable con esa credencial. Los checks de calidad no necesitan credenciales del Project ni entrenamiento completo; comprobar cuotas y límites de Actions antes de activarlos. No afirmar que la automatización funciona hasta probar los eventos reales.

## Referencias

- [GitHub CLI: Projects](https://cli.github.com/manual/gh_project)
- [GitHub CLI: renovar permisos](https://cli.github.com/manual/gh_auth_refresh)
- [Automatización de Projects con Actions](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/automating-projects-using-actions)


