# Skill: Endpoint Diagrams Generator (Component + Sequence)

## 1) Metadata
- **Skill ID:** endpoint-diagrams-generator
- **Version:** 0.1.0
- **Purpose:** Generar diagramas de componentes y de secuencia por cada endpoint detectado en un proyecto.
- **Audience (roles):** Tech Lead, Backend, Frontend, QA, Arquitectura
- **When to use:** Cuando se requiere documentar flujos técnicos por endpoint antes de refactorizar, integrar o auditar.
- **When NOT to use:** Cambios triviales sin impacto en endpoints, tareas sin necesidad de documentación técnica.
- **Sensitive inputs:** No incluir secretos, tokens, credenciales, PII ni URLs internas restringidas.
- **Expected output:** Archivos de diagramas generados en la ruta base del proyecto dentro de `/diagrams`.

## 2) Inputs
Proporciona la información en este formato:

- **Project base path (required):** Ruta base absoluta o relativa del proyecto a analizar.
- **Endpoint scope (optional):** Lista de endpoints a incluir (si se omite, incluir todos los detectados).
- **Protocol/context (optional):** REST, GraphQL, gRPC u otro, si aplica.
- **Output format (optional):** Mermaid (`.mmd`) y/o PlantUML (`.puml`). Por defecto Mermaid.
- **Assumptions/constraints (optional):** Restricciones adicionales del equipo.

## 3) Output
Devuelve **solo** artefactos en archivos dentro de la ruta base del proyecto:

1. Crear carpeta:
   - `/diagrams`

2. Generar índice:
   - `/diagrams/README.md` con:
     - Resumen del alcance
     - Lista de endpoints procesados
     - Referencias a cada diagrama de componentes y secuencia

3. Generar por endpoint (un par de diagramas por cada endpoint):
   - `/diagrams/<endpoint-slug>.component.mmd`
   - `/diagrams/<endpoint-slug>.sequence.mmd`

4. Convención de nombres:
   - `endpoint-slug` en kebab-case basado en método + ruta (ejemplo: `get-api-users-id`)

## 4) Constraints
- No inventar endpoints que no existan en el código o en la especificación provista.
- Si un endpoint no tiene información suficiente para el diagrama, registrarlo en `/diagrams/README.md` como pendiente con motivo.
- No incluir valores sensibles (tokens, secretos, credenciales, payloads reales).
- Mantener consistencia entre nombres de componentes, servicios y repositorios usados en código.
- No proponer tecnologías fuera del stack del proyecto.

## 5) Validation Rules
La salida es válida si:
- Existe la carpeta `/diagrams` en la ruta base del proyecto.
- Existe `/diagrams/README.md`.
- Cada endpoint incluido tiene **2 diagramas**: componentes y secuencia.
- Cada diagrama identifica claramente:
  - Actor o caller
  - Endpoint
  - Capas/componentes involucrados
  - Flujo principal
- No se exponen secretos ni datos sensibles.

## 6) Evidence
Adjunta o referencia estos elementos en el PR o entrega:
- Ruta base utilizada como input.
- Listado de endpoints detectados/procesados.
- Captura o snippet de `/diagrams/README.md`.
- Muestra de al menos un `.component.mmd` y un `.sequence.mmd`.
- Tag de versión del skill, por ejemplo: `skill-endpoint-diagrams-v0.1.0`.
