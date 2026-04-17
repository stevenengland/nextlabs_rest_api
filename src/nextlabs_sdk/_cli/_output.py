from __future__ import annotations

import json
from collections.abc import Sequence
from typing import NamedTuple

from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._output_format import OutputFormat


class ColumnDef(NamedTuple):
    header: str
    field: str


def render_table(
    models: Sequence[BaseModel],
    columns: Sequence[ColumnDef],
    *,
    title: str | None = None,
    console: Console | None = None,
) -> None:
    effective_console = console or Console()
    table = Table(title=title)
    for col in columns:
        table.add_column(col.header)
    for model in models:
        row = [str(getattr(model, column.field)) for column in columns]
        table.add_row(*row)
    effective_console.print(table)


def render_json(source: BaseModel | Sequence[BaseModel]) -> None:
    output: dict[str, object] | list[dict[str, object]]
    if isinstance(source, BaseModel):
        output = source.model_dump(mode="json")
    else:
        output = [entry.model_dump(mode="json") for entry in source]
    print(json.dumps(output, indent=2))


def render(
    ctx: CliContext,
    source: BaseModel | Sequence[BaseModel],
    columns: Sequence[ColumnDef],
    *,
    title: str | None = None,
) -> None:
    if ctx.output_format is OutputFormat.JSON:
        render_json(source)
    elif isinstance(source, BaseModel):
        render_table([source], columns, title=title)
    else:
        render_table(source, columns, title=title)


def print_success(message: str) -> None:
    Console().print(f"[green]✓ {message}[/green]")


def print_error(message: str) -> None:
    Console().print(f"[red]✗ {message}[/red]")
