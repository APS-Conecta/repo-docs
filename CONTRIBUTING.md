# Contribuir — repo-docs

Esta herramienta gobierna la documentación de la organización, así que un cambio aquí cambia la
puerta de control de cada repositorio. Aplica el contrato de toda la organización en
`APS-Conecta/.github`; lo que sigue es lo que difiere.

## La única regla que importa

**Una regla que dispara mal es un defecto de este repositorio, no del documento que marcó.**

Editar a mano el documento para silenciar un hallazgo pierde la lección y deja la regla rota para
todos los demás repositorios. Corregir la regla o la tabla que lee, volver a correr `check --all` y
registrar una línea en [`CHANGELOG.md`](CHANGELOG.md) nombrando el repositorio que la enseñó.

Cada entrada de ese registro es un falso positivo que esta herramienta produjo contra documentación
real. Esa lista es lo más útil que hay aquí — seguir sumándole.

## Artesanía o decisión

Antes de agregar algo, decidir a qué capa pertenece
([ADR 0002](docs/adr/0002-craft-in-the-engine-decisions-in-a-profile.md)):

- **Artesanía** — cierta de la documentación en cualquier parte. Un enlace roto está roto en
  cualquier repositorio. Vive en `scripts/docs.py` como regla.
- **Decisión** — lo que esta organización eligió. Que el código sea AGPL-3.0-or-later, que la
  documentación lectora siga el idioma de su repositorio: inglés por omisión, español con el
  marcador `.github/docs-es` (ADR 0006). Vive en `profiles/aps-conecta.json` como datos.

Una regla que codifica una decisión es el error a evitar; así ganó la regla de licencias sus
primeros tres falsos positivos.

## Agregar una regla

```python
@rule("my-rule", "warn", offline=True)
def _r_mine(ctx):
    """Why this exists. Shown by --explain."""
    yield Finding("my-rule", "warn", file, line, "what is wrong")
```

`offline=False` marca una regla que necesita autenticación con alcance de organización; queda
excluida de la puerta de CI, porque el `GITHUB_TOKEN` de CI no puede leer estado de la
organización. Agregar la justificación a `RATIONALE`.

La severidad es una afirmación sobre la consecuencia, no sobre la confianza. Un `error` bloquea una
fusión. Si no se puede decir qué se rompe, es un `warn`.

## Antes de empujar

```bash
python3 scripts/docs.py selftest      # asserts the destructive paths are safe
python3 scripts/docs.py check --all   # no new findings you did not intend
python3 scripts/docs.py check . --fix # this repo passes its own gate
```

`selftest` debe seguir siendo rápido y sin dependencias. Existe porque `--fix` escribe en
repositorios reales: estuvo a un release de borrar un registro de cambios, y la aserción que atrapó
esa clase es la razón de que `LICENSE` y `CHANGELOG.md` sean semillas y no canon
([ADR 0001](docs/adr/0001-mechanical-and-judgment-are-separate-classes.md)).

## Borrar reglas

Una regla que nunca ha disparado en la organización se borra, no se guarda por si acaso. `DENYLIST`
se midió en cero exclusiones y se eliminó. La cobertura no es el objetivo; atrapar defectos reales
lo es.

## Vocabulario

[`CONTEXT.md`](CONTEXT.md) es el glosario y su vocabulario es estructural (load-bearing): *canon* y
*seed* se ven idénticos al crearse y difieren por completo después, y confundirlos destruye
contenido. Leerlo antes de nombrar cualquier cosa nueva.
