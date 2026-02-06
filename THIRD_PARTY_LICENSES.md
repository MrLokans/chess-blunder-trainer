# Third-Party Licenses

Blunder Tutor is licensed under the GNU Affero General Public License v3.0
(AGPL-3.0). See the `LICENSE` file in the repository root.

This file lists all third-party libraries and assets used by Blunder Tutor,
their licenses, and copyright holders.

---

## Vendored JavaScript Libraries

These files are shipped in `blunder_tutor/web/static/vendor/`.

### chessground 9.1.1

- **Author:** Lichess.org contributors
- **License:** GPL-3.0
- **Source:** [https://github.com/lichess-org/chessground](https://github.com/lichess-org/chessground)
- **Files:** `chessground-9.1.1.min.js`, `chessground-9.1.1.base.css`

### htmx 1.9.10

- **Author:** Big Sky Software (Carson Gross)
- **License:** BSD-2-Clause
- **Source:** [https://github.com/bigskysoftware/htmx](https://github.com/bigskysoftware/htmx)
- **Files:** `htmx-1.9.10.min.js`

Copyright (c) 2020, Big Sky Software.
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.

### Chart.js 4.4.1

- **Author:** Chart.js contributors
- **License:** MIT
- **Source:** [https://github.com/chartjs/Chart.js](https://github.com/chartjs/Chart.js)
- **Files:** `chart-4.4.1.umd.min.js`

Copyright (c) 2014-2024 Chart.js Contributors.
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

### chess.js 0.10.3

- **Author:** Jeff Hlywa
- **License:** BSD-2-Clause
- **Source:** [https://github.com/jhlywa/chess.js](https://github.com/jhlywa/chess.js)
- **Files:** `chess-0.10.3.min.js`

Copyright (c) 2023, Jeff Hlywa.
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.

---

## Chess Piece Sets

Piece images in `blunder_tutor/web/static/pieces/`. These originate from the
[Lichess lila](https://github.com/lichess-org/lila) project and community
contributions.


| Set        | Author                      | License                  |
| ---------- | --------------------------- | ------------------------ |
| cburnett   | Colin M.L. Burnett          | GPL-2.0+                 |
| alpha      | Eric Bentzen                | Permissive (free to use) |
| california | Jerry S.                    | CC BY-NC-SA 4.0          |
| cardinal   | Nochess                     | CC BY-SA 3.0             |
| chessnut   | Alexis Luengas              | GPL-3.0                  |
| companion  | David L. Brown              | Permissive               |
| fresca     | Karthik P.                  | CC BY-SA 4.0             |
| gioco      | Gioco / Lichess             | CC BY-NC-SA 4.0          |
| kosal      | Lichess contributors        | GPL-3.0                  |
| leipzig    | Lichess contributors        | GPL-3.0                  |
| letter     | Lichess contributors        | GPL-3.0                  |
| maestro    | Lichess contributors        | GPL-3.0                  |
| merida     | Armando Hernandez Marroquin | Freeware                 |
| shapes     | Lichess contributors        | GPL-3.0                  |
| staunty    | Lichess contributors        | GPL-3.0                  |
| tatiana    | Lichess contributors        | GPL-3.0                  |
| wikipedia  | Cburnett / Wikimedia        | BSD-3-Clause             |


---

## Python Dependencies

Installed at runtime via `uv`/pip. Not vendored in this repository.


| Package          | License      | Source                                                                                             |
| ---------------- | ------------ | -------------------------------------------------------------------------------------------------- |
| FastAPI          | MIT          | [https://github.com/tiangolo/fastapi](https://github.com/tiangolo/fastapi)                         |
| Uvicorn          | BSD-3-Clause | [https://github.com/encode/uvicorn](https://github.com/encode/uvicorn)                             |
| SQLAlchemy       | MIT          | [https://github.com/sqlalchemy/sqlalchemy](https://github.com/sqlalchemy/sqlalchemy)               |
| aiosqlite        | MIT          | [https://github.com/omnilib/aiosqlite](https://github.com/omnilib/aiosqlite)                       |
| Alembic          | MIT          | [https://github.com/sqlalchemy/alembic](https://github.com/sqlalchemy/alembic)                     |
| Jinja2           | BSD-3-Clause | [https://github.com/pallets/jinja](https://github.com/pallets/jinja)                               |
| python-chess     | GPL-3.0      | [https://github.com/niklasf/python-chess](https://github.com/niklasf/python-chess)                 |
| httpx            | BSD-3-Clause | [https://github.com/encode/httpx](https://github.com/encode/httpx)                                 |
| APScheduler      | MIT          | [https://github.com/agronholm/apscheduler](https://github.com/agronholm/apscheduler)               |
| websockets       | BSD-3-Clause | [https://github.com/python-websockets/websockets](https://github.com/python-websockets/websockets) |
| python-multipart | Apache-2.0   | [https://github.com/Kludex/python-multipart](https://github.com/Kludex/python-multipart)           |
| tqdm             | MIT/MPL-2.0  | [https://github.com/tqdm/tqdm](https://github.com/tqdm/tqdm)                                       |
| hyx              | MIT          | [https://github.com/roma-glushko/hyx](https://github.com/roma-glushko/hyx)                         |
| fast-depends     | MIT          | [https://github.com/Lancetnik/FastDepends](https://github.com/Lancetnik/FastDepends)               |


### Dev-only


| Package        | License    | Source                                                                                       |
| -------------- | ---------- | -------------------------------------------------------------------------------------------- |
| pytest         | MIT        | [https://github.com/pytest-dev/pytest](https://github.com/pytest-dev/pytest)                 |
| pytest-asyncio | Apache-2.0 | [https://github.com/pytest-dev/pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio) |
| pytest-cov     | MIT        | [https://github.com/pytest-dev/pytest-cov](https://github.com/pytest-dev/pytest-cov)         |
| Ruff           | MIT        | [https://github.com/astral-sh/ruff](https://github.com/astral-sh/ruff)                       |


---

## External Services

- **Lichess API** — used to fetch games. Free, open-source platform. [https://lichess.org](https://lichess.org)
- **Chess.com API** — used to fetch games. [https://chess.com](https://chess.com)
- **Stockfish** — chess engine used for analysis (installed separately by user or distributed in the Docker container). GPL-3.0. [https://stockfishchess.org](https://stockfishchess.org)

