## Frontend (TypeScript)

**Stack:** TypeScript 5.x (strict), Preact 10.x (islands architecture), Vite 6.x, Vitest 3.x, ESLint 9.x with typescript-eslint

**Structure:** `frontend/src/` contains all TS source. One entry point per page in `src/<page>/index.tsx`. Shared Preact components in `src/components/`. Shared hooks in `src/hooks/`. Shared utilities in `src/shared/`. Types in `src/types/`. Vendored lib types in `src/vendor.d.ts`.

**Preact:** All pages use Preact components.

**Anti-patterns — wrong vs right:**
```
catch (err: any)                  → catch (err: unknown) + type narrowing
as SomeType                       → type guard or satisfies
// @ts-ignore                     → fix the type error
process.env.X                     → import.meta.env.VITE_X
new WebSocket(url)                → use shared/websocket-client.ts
fetch('/api/...')                  → use shared/api.ts client
any                               → unknown, then narrow
e.target as HTMLElement            → e.currentTarget (already typed)
{{ data_json | safe }}             → {{ data | tojson }} in Jinja
{} as SomeType (initial state)    → null + render guard
DOM side effects in handlers      → useEffect synced on state
'Hardcoded English'               → t('i18n.key')
<div class="btn..."> / className="btn-..."  → use <Button> from components/Button
```

**Canonical patterns:**
```ts
// API call
import { client } from '../shared/api';
const puzzle = await client.trainer.getPuzzle({ color: 'white' });

// Event bus (typed)
import { bus } from '../shared/event-bus';
bus.emit('puzzle:loaded', { fen, moveIndex, gameId });

// Feature check
import { hasFeature } from '../shared/features';
if (hasFeature('trainer.tactics')) { ... }
```

**Import boundaries:** Page modules (`trainer/`, `dashboard/`, etc.) CANNOT import from other page modules. Shared code goes in `shared/`. Enforced by ESLint `no-restricted-imports` (configured in `frontend/eslint.config.ts`).
