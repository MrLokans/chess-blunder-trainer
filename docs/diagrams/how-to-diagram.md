# Architecture Diagrams

Use D2 with the ELK layout for maintained architecture diagrams.

| Item | Location |
|---|---|
| D2 source | `docs/diagrams/<name>.d2` |
| Shared styles | `docs/diagrams/styles/classes.d2` |
| Committed output | `docs/diagrams/generated/<name>.svg` |
| Current example | `docs/diagrams/components.d2` |


## Start a diagram

Import the shared classes on the first line and choose one layout direction:

```d2
...@styles/classes.d2

direction: down

browser: Browser {class: external}
app: Web App {class: service}
db: SQLite {class: database}

browser -> app: HTTP
app -> db: reads + writes
```

Use the existing classes rather than copying colors into each file:

| Class | Use |
|---|---|
| `service` | Business logic and application services |
| `repository` | Data access |
| `database` | Persistent stores |
| `external` | Users and external APIs |
| `engine` | Stockfish and process-level coordinators |
| `infra` | Middleware, schedulers, events, and other plumbing |
| `container` | A visible group of related nodes |

Color an edge only when a protocol boundary matters. Most edges should keep the default style.

```d2
browser -> app: HTTP {style.stroke: "#D42828"; style.stroke-width: 2}
app -> stockfish: UCI {style.stroke: "#D42828"; style.stroke-width: 2}
app -> lichess: HTTPS {style.stroke: "#F2C12E"}
```

## Keep the graph readable

- Show one primary flow direction: `down` is the default; use `right` when it reads better.
- Represent bidirectional traffic with one edge, such as `HTTP + WebSocket`, instead of opposing arrows.
- Keep containers one level deep. Deep cross-container edges produce poor ELK routing.
- Show request, data, and protocol flow. Omit dependency injection, construction, logging, metrics, and health checks unless they are the subject.
- Prefer a second focused diagram over adding detail to a crowded one.
- Use short labels. Put explanations in [`../architecture/overview.md`](../architecture/overview.md), not in nodes.

A container lays peers side by side with `direction: right`:

```d2
repos: Repositories {
  class: container
  direction: right
  game: Game {class: repository}
  analysis: Analysis {class: repository}
}
```

Internal edges can override that visual direction. If peers unexpectedly stack, remove unnecessary edges between them.

## Validate and render

Validate the source:

```bash
d2 validate docs/diagrams/<name>.d2
```

Render the committed SVG with the project's ELK spacing:

```bash
d2 --layout elk \
  --elk-nodeNodeBetweenLayers 25 \
  --elk-padding '[top=15,left=15,bottom=15,right=15]' \
  --elk-edgeNodeBetweenLayers 10 \
  --pad 30 \
  docs/diagrams/<name>.d2 docs/diagrams/generated/<name>.svg
```

Render a PNG with the same flags and inspect it before finishing:

```bash
d2 --layout elk \
  --elk-nodeNodeBetweenLayers 25 \
  --elk-padding '[top=15,left=15,bottom=15,right=15]' \
  --elk-edgeNodeBetweenLayers 10 \
  --pad 30 \
  docs/diagrams/<name>.d2 /tmp/<name>.png
```

Check that:

- the main flow is obvious without tracing crossed edges;
- labels fit and remain legible at normal document width;
- related nodes stay together;
- containers do not create large empty areas;
- the diagram matches current code and [`../architecture/overview.md`](../architecture/overview.md).

Delete the temporary PNG. Commit the `.d2` source and generated `.svg` together.

## D2 pitfalls

Avoid attribute and board keywords as node IDs, including `style`, `shape`, `label`, `icon`, `link`, `classes`, `vars`, `layers`, `scenarios`, `top`, `bottom`, `left`, and `right`. Prefix the ID when needed: `layer_map`, `right_side`, or `style_node`.

Do not use transparent containers for invisible grouping. D2 still renders the container ID as a label; use a visible `container` or let edge proximity drive layout.

If ELK produces a tangled result, simplify the graph before adding layout constraints: remove secondary edges, flatten containers, or merge nodes that do not need separate identities.
