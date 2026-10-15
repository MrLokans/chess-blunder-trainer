from __future__ import annotations

import abc
from typing import Any, ClassVar


class BaseJob(abc.ABC):
    job_identifier: ClassVar[str]

    @abc.abstractmethod
    async def execute(self, job_id: str, **kwargs: Any) -> dict[str, Any]: ...
