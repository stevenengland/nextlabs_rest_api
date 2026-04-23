from __future__ import annotations

from typing import Annotated

import typer
from pydantic import BaseModel
from rich.console import Console

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._detail_renderers import register_detail_renderer
from nextlabs_sdk._cli._error_handler import cli_error_handler
from nextlabs_sdk._cli._output import ColumnDef, print_error, print_success, render
from nextlabs_sdk._cloudaz._models import Tag, TagType

tags_app = typer.Typer(help="Tag management commands")

_TAG_COLUMNS = (
    ColumnDef("ID", "id"),
    ColumnDef("Key", "key"),
    ColumnDef("Label", "label"),
    ColumnDef("Type", "type"),
    ColumnDef("Status", "status"),
)


def _parse_tag_type(raw_type: str) -> TagType:
    try:
        return TagType(raw_type.upper())
    except ValueError:
        valid = ", ".join(tag.value for tag in TagType)
        print_error(f"Invalid tag type: {raw_type}. Valid types: {valid}")
        raise typer.Exit(code=1)


@tags_app.command(name="list")
@cli_error_handler
def list_tags(
    ctx: typer.Context,
    tag_type: Annotated[str, typer.Argument(help="Tag type (e.g. COMPONENT_TAG)")],
) -> None:
    """List tags of a given type."""
    cli_ctx: CliContext = ctx.obj
    parsed_type = _parse_tag_type(tag_type)
    client = _client_factory.make_cloudaz_client(cli_ctx)
    tags = list(client.tags.list(parsed_type))
    render(cli_ctx, tags, _TAG_COLUMNS, title="Tags")


@tags_app.command()
@cli_error_handler
def get(
    ctx: typer.Context,
    tag_id: Annotated[int, typer.Argument(help="Tag ID")],
) -> None:
    """Get a tag by ID."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    tag = client.tags.get(tag_id)
    render(cli_ctx, tag, _TAG_COLUMNS)


@tags_app.command()
@cli_error_handler
def create(
    ctx: typer.Context,
    tag_type: Annotated[str, typer.Argument(help="Tag type (e.g. COMPONENT_TAG)")],
    key: Annotated[str, typer.Option(help="Tag key")],
    label: Annotated[str, typer.Option(help="Tag label")],
) -> None:
    """Create a new tag."""
    cli_ctx: CliContext = ctx.obj
    parsed_type = _parse_tag_type(tag_type)
    client = _client_factory.make_cloudaz_client(cli_ctx)
    tag_id = client.tags.create(parsed_type, key=key, label=label)
    print_success(f"Created tag with ID {tag_id}")


@tags_app.command()
@cli_error_handler
def delete(
    ctx: typer.Context,
    tag_id: Annotated[int, typer.Argument(help="Tag ID")],
) -> None:
    """Delete a tag by ID."""
    cli_ctx: CliContext = ctx.obj
    client = _client_factory.make_cloudaz_client(cli_ctx)
    client.tags.delete(tag_id)
    print_success(f"Deleted tag {tag_id}")


def _render_tag_detail(model: BaseModel, console: Console) -> None:
    assert isinstance(model, Tag)
    console.print(f"[bold]Tag[/bold] {model.id}")
    console.print(f"  [bold]Key[/bold]:    {model.key}")
    console.print(f"  [bold]Label[/bold]:  {model.label}")
    console.print(f"  [bold]Type[/bold]:   {model.type.value if model.type else ''}")
    console.print(f"  [bold]Status[/bold]: {model.status}")


register_detail_renderer(Tag, _render_tag_detail)
