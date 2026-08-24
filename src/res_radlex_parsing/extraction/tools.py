"""CLI entry points backing the Pi RadLex tools (query_radlex_graph, get_concept,
propose_concept).

Invoked as a subprocess (``python -m res_radlex_parsing.extraction.tools ...``) by
``.pi/extensions/radlex_tools.ts``, once per tool call. Each subcommand uses
res_radlex_parsing directly via module-level imports (RadLexGraphQuery for reads; a
plain JSONL append for propose_concept) and prints a single JSON object to stdout for
the extension to relay back to the LLM.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from res_radlex_parsing.graph.query import RadLexGraphQuery

DEFAULT_DB_PATH = Path("data/intermediate/radlex.duckdb")
DEFAULT_CANDIDATES_PATH = Path("data/output/candidates.jsonl")


def search_concepts(
    text: str, limit: int = 10, db_path: Path = DEFAULT_DB_PATH
) -> list[dict[str, Any]]:
    """Searches RadLex node labels/synonyms for a text match, best match first.

    Args:
        text: Free text to match against node labels/synonyms.
        limit: Maximum number of matches to return.
        db_path: Filesystem path to the persisted RadLex DuckDB database.

    Returns:
        A list of JSON-serializable dicts with keys ``rid``, ``label``, ``synonyms``,
        ``is_obsolete``, ``replaced_by_rid``, ``match_type`` and ``bm25``.
        ``match_type`` is ``exact`` when the label or a synonym is literally equal to
        the search text, and ``candidate`` when the concept was found by full-text
        search and should be confirmed before use.
    """
    with RadLexGraphQuery(db_path).load() as query:
        return query.search(text, limit=limit).to_pylist()


def get_concept(rid: str, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    """Looks up a single RadLex concept's attributes and immediate hierarchy.

    Args:
        rid: The RadLex identifier to look up.
        db_path: Filesystem path to the persisted RadLex DuckDB database.

    Returns:
        A dict with the node's attributes (label, synonyms, definition, is_obsolete,
        replaced_by_rid) plus ``parents`` and ``children`` RID lists (via the ``is_a``
        hierarchy), or ``None`` if ``rid`` is not in the graph.
    """
    with RadLexGraphQuery(db_path).load() as query:
        node = query.get_node(rid)
        if node is None:
            return None

        return {
            "rid": rid,
            **node,
            "parents": query.get_parents(rid),
            "children": query.get_children(rid),
        }


def propose_concept(
    name: str,
    parent_rid: str,
    rationale: str,
    relationships: list[dict[str, str]] | None = None,
    candidates_path: Path = DEFAULT_CANDIDATES_PATH,
) -> dict[str, Any]:
    """Appends a candidate new concept to the review file.

    Args:
        name: Proposed display name for the new concept.
        parent_rid: RID of the suggested parent concept in the existing graph (the
            candidate's ``is_a`` placement).
        rationale: Free-text justification for why this concept appears to be
            missing from RadLex.
        relationships: Additional non-hierarchy relations for the candidate, each a
            dict with ``relation_type`` (e.g. ``"Part_Of"``, ``"Branch_Of"``,
            ``"Contained_In"``) and ``target_rid`` (an existing RID in the graph).
            Defaults to an empty list if not given.
        candidates_path: Filesystem path to the JSONL file candidates are appended
            to. Parent directory is created if it does not exist.

    Returns:
        The JSON-serializable record that was written (echoed back for
        confirmation).
    """
    record = {
        "name": name,
        "parent_rid": parent_rid,
        "rationale": rationale,
        "relationships": relationships or [],
    }

    candidates_path.parent.mkdir(parents=True, exist_ok=True)
    with candidates_path.open("a") as f:
        f.write(json.dumps(record) + "\n")

    return record


@click.group()
def cli() -> None:
    """RadLex knowledge graph tools backing the Pi extraction/suggestion skills."""


@cli.command("search")
@click.option(
    "--text",
    required=True,
    help="Free text to match against RadLex concept labels and synonyms.",
)
@click.option(
    "--limit",
    default=10,
    show_default=True,
    help="Maximum number of matching concepts to return.",
)
@click.option(
    "--db-path",
    default=str(DEFAULT_DB_PATH),
    show_default=True,
    type=click.Path(path_type=Path),
    help="Path to the persisted RadLex DuckDB database, as written by RadLexGraphBuilder.save().",
)
def search_command(text: str, limit: int, db_path: Path) -> None:
    """Search RadLex concept labels and synonyms for a text match, printed as JSON."""
    click.echo(json.dumps(search_concepts(text, limit, db_path)))


@cli.command("get-concept")
@click.option(
    "--rid",
    required=True,
    help="RadLex identifier to look up, e.g. RID1327.",
)
@click.option(
    "--db-path",
    default=str(DEFAULT_DB_PATH),
    show_default=True,
    type=click.Path(path_type=Path),
    help="Path to the persisted RadLex DuckDB database, as written by RadLexGraphBuilder.save().",
)
def get_concept_command(rid: str, db_path: Path) -> None:
    """Look up a RadLex concept's attributes and immediate is_a parents/children,
    printed as JSON."""
    click.echo(json.dumps(get_concept(rid, db_path)))


@cli.command("propose-concept")
@click.option(
    "--name",
    required=True,
    help="Proposed display name for the new concept.",
)
@click.option(
    "--parent-rid",
    required=True,
    help="RID of the suggested parent concept in the existing graph (the candidate's is_a placement).",
)
@click.option(
    "--rationale",
    required=True,
    help="Free-text justification for why this concept appears to be missing from RadLex.",
)
@click.option(
    "--relationships",
    default="[]",
    show_default=True,
    help=(
        "JSON array of additional non-hierarchy relations for the candidate, each "
        'an object like {"relation_type": "Part_Of", "target_rid": "RID123"}.'
    ),
)
@click.option(
    "--candidates-path",
    default=str(DEFAULT_CANDIDATES_PATH),
    show_default=True,
    type=click.Path(path_type=Path),
    help="JSONL file to append the candidate record to.",
)
def propose_concept_command(
    name: str,
    parent_rid: str,
    rationale: str,
    relationships: str,
    candidates_path: Path,
) -> None:
    """Record a candidate new RadLex concept not currently in the graph, for later
    review."""
    click.echo(
        json.dumps(
            propose_concept(
                name, parent_rid, rationale, json.loads(relationships), candidates_path
            )
        )
    )


if __name__ == "__main__":
    cli()
