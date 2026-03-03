"""Base classes for lifespan dependency injection."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from inspect import isabstract
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, FastAPI


class LifespanDependency(ABC):
    """All lifespan dependencies must inherit from this class."""

    _registry: list[type[LifespanDependency]] = []

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if not isabstract(cls) and cls not in LifespanDependency._registry:
            LifespanDependency._registry.append(cls)

    @staticmethod
    @abstractmethod
    def __call__(*args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    @asynccontextmanager
    async def lifespan(self, app: FastAPI) -> AsyncGenerator[None, None]:
        yield

    def get_routers(self) -> list[APIRouter]:
        """Override to contribute routers to the application under api prefix."""
        return []

    @classmethod
    def depends(cls) -> Any:
        return Depends(cls.__call__)
