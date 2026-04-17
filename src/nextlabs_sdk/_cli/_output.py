from __future__ import annotations

import json
from collections.abc import Sequence
from typing import NamedTuple

from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._detail_renderers import render_detail
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
        table.add_column(col.header, overflow="fold", no_wrap=False)
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
    wide_columns: Sequence[ColumnDef] | None = None,
) -> None:
    if ctx.output_format is OutputFormat.JSON:
        render_json(source)
        return
    if ctx.output_format is OutputFormat.DETAIL:
        render_detail(source, console=Console())
        return
    models: Sequence[BaseModel] = [source] if isinstance(source, BaseModel) else source
    if ctx.output_format is OutputFormat.WIDE:
        combined = tuple(columns) + tuple(wide_columns or ())
        render_table(models, combined, title=title)
        return
    render_table(models, columns, title=title)


def print_success(message: str) -> None:
    Console().print(f"[green]✓ {message}[/green]")


def print_error(message: str) -> None:
    Console().print(f"[red]✗ {message}[/red]")
