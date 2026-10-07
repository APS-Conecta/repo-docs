# Política de seguridad — repo-docs

## Alcance

Una herramienta de documentación para los repositorios propios de esta organización. No guarda
datos de pacientes ni datos clínicos, y no procesa entrada en tiempo de ejecución: lee Markdown y
metadatos de repositorios, desde disco y desde la API de GitHub.

El repositorio es privado. Esta política existe porque la herramienta tiene más autoridad de la que
una herramienta de documentación suele tener.

## Qué puede hacer esta herramienta

Corre con las credenciales `gh` de quien la opera, que llevan `repo` y `admin:org`. Bajo
`--apply-settings` cambia configuraciones de la organización y de repositorios, no únicamente
documentación ([ADR 0003](docs/adr/0003-the-tool-changes-github-settings.md)).

Esa ampliación del radio de explosión es deliberada, y está cercada:

- Las configuraciones cambian **únicamente** bajo un `--apply-settings` explícito. `--fix` nunca
  las toca.
- `org-2fa` se niega mientras algún miembro carezca de 2FA, porque aplicar la política remueve a
  esos miembros — y esta organización tiene un miembro, que es además su dueño.
- `--fix` escribe únicamente la clase mecánica. Nunca reescribe prosa y nunca restaura una semilla
  (`LICENSE`, `CHANGELOG.md`), porque restaurar una destruye contenido acumulado.
- `pr` abre pull requests en borrador únicamente, commitea únicamente rutas de documentación y se
  niega con un árbol de trabajo que contenga cualquier otra cosa. Nunca fusiona, nunca hace
  force-push y nunca toca la rama por defecto.

`selftest` aserta estos caminos. Tratar un cambio que debilite uno de ellos como un cambio de
seguridad, no como una refactorización.

## Manejo de credenciales

La herramienta no guarda credenciales. Invoca `gh`, que usa la sesión existente de quien la opera.
Nunca escribe tokens a disco y nunca imprime respuestas de la API que los contengan.

`config.json` guarda una ruta del sistema de archivos y está en `.gitignore`. Nada más es local a la
máquina.

## Reportar una vulnerabilidad

No abrir un issue público. Usar el reporte privado de GitHub en este repositorio, o contactar al
mantenedor a través del [perfil de la organización](https://github.com/APS-Conecta).

Los reportes sobre las barreras de arriba son los que vale la pena enviar — en particular,
cualquier camino que deje a `--fix` o a `pr` escribir fuera de la superficie de documentación, o
que logre aplicar una configuración sin el flag explícito.

## Fuera de alcance

- La herramienta confía en los repositorios a los que se le apunta. No es una sandbox y no se
  defiende de Markdown hostil; cada repositorio que lee fue escrito dentro de la organización.
- `gitleaks`, cuando está instalado, se invoca como escáner externo. Sus hallazgos y sus falsos
  negativos son suyos.
