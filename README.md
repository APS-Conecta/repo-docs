# repo-docs

Control de documentación para los repositorios de APS Conecta. Audita lo que ya está escrito,
corrige lo que tiene una única respuesta demostrable y genera el andamiaje de lo que falta.

## Qué es

**Es un auditor, primero.** La documentación de la organización ya existe y ya está derivando:
cuatro archivos de `gestion` discrepaban sobre el tamaño del equipo, tres repositorios declaraban
una licencia que su archivo `LICENSE` contradecía, y veintidós ADR no tenían campo de estado entre
todos. Esta herramienta encuentra esa clase de defecto y, donde una máquina puede resolver la
pregunta, la corrige.

**No es** un asistente de escritura: no puede hacer buena la prosa. Comprueba que la documentación
esté estructuralmente completa y factualmente consistente — la parte que sí se puede comprobar — y
deja la escritura en manos de una persona o de un modelo que trabaje desde el contrato de secciones
que la herramienta genera.

**No es** una herramienta genérica. Codifica las decisiones de esta organización en
`profiles/aps-conecta.json`; el motor es portable, la política no, y esa separación es deliberada
([ADR 0002](docs/adr/0002-craft-in-the-engine-decisions-in-a-profile.md)).

## Documentación

### Comandos

| Comando | Hace |
|---|---|
| `discover [--clone]` | Mapea los clones administrados; rechaza dueños sin perfil |
| `scan <repo>` | Inventario como JSON. Nunca escribe |
| `check <repo\|--all>` | La puerta de control. `--fix`, `--offline`, `--explain`, `--save-baseline` |
| `outline <repo>` | El contrato de secciones del README y qué le falta |
| `licences <repo>` | Lo que el repositorio declara, y cada licencia de terceros presente |
| `scaffold <repo> --write` | Escribe los archivos que faltan. Nunca sobrescribe |
| `harvest` | Refresca `canon/` desde el ejemplar del perfil |
| `settings <repo>` | Sonda el estado de GitHub; `--apply-settings` para cambiarlo |
| `pr <repo>` | PR en borrador, únicamente con cambios de documentación |
| `audit <repo>` | Prompt para una lectura completa por modelo. No es parte de la puerta |

Las reglas, los hechos y las configuraciones son registros: agregar uno es una función y un
decorador. La política es una tabla en un perfil. Si afinar exige editar el cuerpo de una función,
la costura está mal.

### Consumidores

Nada importa este repositorio. Se invoca como CLI y se replica en cada repositorio gobernado como
`.github/repo-docs.py`, donde el workflow `docs` corre sus reglas offline en cada pull request.
`canon-drift` mantiene esas copias idénticas a esta, así que este repositorio es el único lugar
donde el motor se edita.

Cambiar una regla cambia entonces la puerta de control de cada repositorio en el próximo `--fix`.
Leer [`CONTEXT.md`](CONTEXT.md) antes de agregar una: el vocabulario es estructural.

Las decisiones viven como ADR en [`docs/adr/`](docs/adr) — por qué el checker se replica en cada
repositorio ([ADR 0004](docs/adr/0004-the-checker-is-vendored-into-every-repo.md)), por qué cambia
configuraciones de GitHub ([ADR 0003](docs/adr/0003-the-tool-changes-github-settings.md)) y por qué
la documentación lectora de este repositorio está en español
([ADR 0006](docs/adr/0006-documentacion-en-espanol.md)). El árbol de archivos por nivel está en
[`references/layout.md`](references/layout.md); las convenciones — Diátaxis, Keep a Changelog,
MADR — en [`references/conventions.md`](references/conventions.md).

## Estado

Funciona y está en su primer despliegue. 29 reglas, 5 hechos, 5 sondas de configuración, un perfil
de dueño.

El barrido semanal audita los doce repositorios del censo de la organización; este repositorio
queda fuera del censo y se gobierna a sí mismo: pasa su propia puerta de control. La documentación
lectora de este repositorio está en español según el
[ADR 0006](docs/adr/0006-documentacion-en-espanol.md), activado con el marcador `.github/docs-es`.

Pendiente: ensanchar el PAT del barrido para que el registro del censo vea lo que el barrido ve
(tarea abierta en este repositorio).

## Inicio rápido de desarrollo

Todo lo que sigue corre en el host, desde cualquier directorio.

1. Apuntar la herramienta a los clones. Corre una vez por máquina.

   ```bash
   cp config.example.json config.json
   $EDITOR config.json          # set "root" to the directory holding your clones
   ```

   `config.json` está en `.gitignore` — guarda una ruta de máquina, nunca política.

2. Confirmar que la herramienta ve los repositorios.

   ```bash
   python3 scripts/docs.py discover
   ```

   Devuelve un mapa JSON de cada clon cuyo dueño tiene perfil. Los dueños sin perfil quedan bajo
   `unmanaged` y nunca se tocan. Un mapa `repos` vacío significa que `root` está mal.

3. Auditar un repositorio.

   ```bash
   python3 scripts/docs.py check gestion --explain
   ```

   Código de salida 0 significa sin errores; 1 significa al menos uno. Los avisos nunca fallan la
   corrida. `--explain` imprime por qué existe cada regla, así que un hallazgo en desacuerdo nombra
   la línea a editar.

4. Auditar todo y registrar el resultado.

   ```bash
   python3 scripts/docs.py check --all --save-baseline
   ```

   Las corridas posteriores se comparan con `baseline.json`: qué es nuevo, qué se resolvió, qué
   sigue abierto.

Si un paso falla, el mensaje nombra la causa. La más común es `root` apuntando a un directorio sin
clones.

### Instalación

Sin dependencias. Python 3.9 o posterior, `git`, y `gh` autenticado con `repo` y `admin:org` para
las reglas que leen estado de la organización.

La skill se carga por symlink, así que el repositorio y la skill son los mismos archivos:

```bash
ln -s "$PWD" ~/.claude/skills/repo-docs
```

Verificar con `python3 scripts/docs.py selftest`, que construye un repositorio temporal y aserta
que los caminos destructivos son seguros.

## Licencia

GNU Affero General Public License v3.0 o posterior — véase [`LICENSE`](LICENSE). Coincide con la
postura de toda la organización registrada en el
[ADR-0010 de gestion](https://github.com/APS-Conecta/gestion/blob/main/docs/adr/0010-agpl-across-the-org.md),
movida a `gestion` desde un repositorio de producto el 2026-08-08, porque una decisión de toda la
organización no vive en el repositorio de un producto único. La herramienta no depende de nada
fuera de la biblioteca estándar de Python, así que no hay avisos de terceros que llevar; los avisos
y licencias de la organización viven en
[Aviso y licencias](https://aps-conecta.github.io/documentation/aviso.html).
