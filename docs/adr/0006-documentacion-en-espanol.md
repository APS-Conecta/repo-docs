# ADR 0006: Documentación en español

## Estado

- Status: Aceptada (2026-10-06)

## Contexto

La postura de idioma nunca se había registrado como un ADR: el perfil decía `doc_language: "en"` —
documentación de repositorio en inglés — y la única excepción era el `README.md` bilingüe del
perfil de la organización. Mientras tanto, la organización opera en Chile, el personal clínico lee
en español y ya existían documentos deliberadamente en español (las convenciones del personal, la
guía clínica), listados como exenciones porque la política no tenía un lugar para ellos. Una regla
de inglés para todos por igual empujaba a traducir la historia fechada o a mantener el español
fuera de la política.

## Decisión

La documentación lectora de los repositorios con marcador es español, según la lista obligatoria
(`must_be_spanish`) del perfil: `README.md`, `CONTRIBUTING.md`, `SECURITY.md` y equivalentes. El
opt-in es un archivo marcador vacío, `.github/docs-es`; sin marcador, el régimen es el histórico:
inglés, con las reglas existentes byte a byte iguales.

El reparto completo del idioma queda registrado: la prosa para personas — `README.md`, el sitio de
documentación, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, los ADR nuevos y los títulos
de issues — es español; el código, los identificadores, los comentarios, los títulos de PR,
`AGENTS.md`, `CLAUDE.md` y `CONTEXT.md` quedan en inglés.

El registro es español neutro: tercera persona o impersonal, pasos en infinitivo, hechos
verificados en afirmativo. Los manuales viven únicamente en APS-Conecta/documentation — la regla
`retired-paths` lo exige mecánicamente en cada repositorio con marcador. Los ADR existentes y las
entradas pasadas de los registros de cambios no se traducen: la historia fechada queda como se
escribió. El nombre propio de la licencia se mantiene en inglés («GNU Affero General Public
License v3.0 o posterior»), porque las reglas que lo leen buscan tokens en inglés.

Esta decisión reemplaza la postura implícita `doc_language: "en"` — que nunca se registró como ADR
— y deja sin efecto su lectura como «inglés para todo lo lectora».

## Consecuencias

- El repositorio que opta reescribe su superficie lectora al español; `doc-language-es` exige el
  cuerpo en español archivo por archivo (ERROR) y `readme-sections` exige el contrato de cinco
  secciones H2 en orden (ERROR).
- La regla agregada `doc-language` se suprime en los repositorios con marcador — la regla por
  archivo es la que manda desde el opt-in — y queda byte a byte igual en el resto.
- La historia fechada (ADR, registros de cambios) no se traduce, y la regla por archivo no la
  exige.
- El perfil enseña el régimen dual en `_comment_language`; este ADR es su referencia.
- Los repositorios sin marcador no cambian en nada: dormencia silenciosa, sin hallazgos nuevos.
