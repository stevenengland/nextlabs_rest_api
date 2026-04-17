from __future__ import annotations

from collections.abc import Callable, Sequence

from pydantic import BaseModel
from rich.console import Console

DetailRenderer = Callable[[BaseModel, Console], None]


class _Registry:
    _renderers: dict[type[BaseModel], DetailRenderer] = {}

    @classmethod
    def register(cls, model_cls: type[BaseModel], fn: DetailRenderer) -> None:
        cls._renderers[model_cls] = fn

    @classmethod
    def get(cls, model_cls: type[BaseModel]) -> DetailRenderer | None:
        return cls._renderers.get(model_cls)


def register_detail_renderer(model_cls: type[BaseModel], fn: DetailRenderer) -> None:
    """Register a detail renderer for a Pydantic model class."""
    _Registry.register(model_cls, fn)


def _render_fallback(model: BaseModel, console: Console) -> None:
    console.print(f"[bold]{type(model).__name__}[/bold]")
    for field, field_value in model.model_dump(mode="json").items():
        console.print(f"  [bold]{field}[/bold]: {field_value}")


def render_detail(
    source: BaseModel | Sequence[BaseModel],
    *,
    console: Console | None = None,
) -> None:
    """Render one or more Pydantic models using registered detail renderers."""
    effective = console or Console()
    if isinstance(source, BaseModel):
        entries: list[BaseModel] = [source]
    else:
        entries = list(source)
    for index, model in enumerate(entries):
        if index > 0:
            effective.print("")
        renderer = _Registry.get(type(model)) or _render_fallback
        renderer(model, effective)
