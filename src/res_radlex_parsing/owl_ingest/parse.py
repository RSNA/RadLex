"""Parse the RadLex OWL/RDF-XML source file into plain Python records.

Reads ``data/staging/RadLex.owl`` with :mod:`rdflib` (plain triple extraction — no OWL
reasoning is required for this standard RDF/XML file) via :class:`RadLexOwlParser`,
which yields one :class:`RadLexClassRecord` per ``owl:Class`` subject for downstream
consumption by :mod:`res_radlex_parsing.graph.build_graph`. Each record carries:

- ``rdfs:label`` (``xml:lang="en"``) — display name.
- ``RID:Synonym`` — alternate terms.
- ``RID:Definition`` — free-text definition (sparse).
- ``rdfs:subClassOf rdf:resource="..."`` — direct ``is_a`` parent edges.
- ``rdfs:subClassOf`` -> ``owl:Restriction`` blocks (``owl:onProperty`` +
  ``owl:someValuesFrom``) — typed relations beyond ``is_a`` (``Part_Of``, ``Has_Part``,
  ``Branch_Of``, ``Contained_In``, ``Member_Of``, etc.).
- ``RID:Replaced_by`` / ``RID:Preferred_Name_for_Obsolete`` — obsolescence markers.

This module has no knowledge of networkx or DuckDB; it only turns RDF triples into
plain records for the graph-building stage to consume.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import rdflib

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TripleRow:
    """A single flattened RDF triple, as stored in the parsed triples table.

    Attributes:
        subject: Subject RID or blank node id.
        predicate: Predicate local name (e.g. ``"label"``, ``"subClassOf"``).
        object: Object value — a literal string, or a bare RID/blank node id when
            the object is a resource.
        is_resource: ``True`` if ``object`` is a URI/blank node reference rather
            than a literal value.
        lang: The ``xml:lang`` tag for literal objects, if any.
    """

    subject: str
    predicate: str
    object: str
    is_resource: bool
    lang: str | None


class RadLexOwlParser:
    """Loads, parses, and saves the RadLex OWL/RDF-XML source as a flat triples table.

    A pure parsing utility: reads the RDF/XML file into memory, flattens every triple
    into a tabular structure, and writes that structure to disk in a format DuckDB's
    Python module can read directly. Graph-building and querying are out of scope for
    this class and are handled downstream.

    Methods are designed for chaining, e.g.::

        RadLexOwlParser(owl_path).load().parse().save(output_path)

    Attributes:
        owl_path: Filesystem path to the source ``RadLex.owl`` file.
    """

    def __init__(self, owl_path: Path) -> None:
        """Initializes the parser without reading the file.

        Args:
            owl_path: Filesystem path to the source ``RadLex.owl`` file.
        """
        self.owl_path = owl_path
        self._graph: rdflib.Graph | None = None
        self._triples: pa.Table | None = None

    def load(self) -> RadLexOwlParser:
        """Reads the OWL/RDF-XML file into an in-memory ``rdflib.Graph``.

        Must be called before :meth:`parse`.

        Returns:
            This parser instance, to support method chaining.

        Raises:
            OSError: If ``owl_path`` cannot be read.
        """

        logger.info("Loading RadLex OWL fiel from %s", self.owl_path)

        graph = rdflib.Graph()
        graph.parse(self.owl_path, format="xml")
        self._graph = graph

        return self

    def parse(self) -> RadLexOwlParser:
        """Flattens the loaded RDF graph into a tabular triples structure.

        Walks every triple in the loaded graph exactly once, resolving subject and
        resource-valued object URIs down to bare RadLex RIDs, and holds the result in
        memory for :meth:`save`. Produces a table with one row per triple and columns:

        - ``subject`` (str): subject RID or blank node id.
        - ``predicate`` (str): predicate local name (e.g. ``"label"``,
        ``"subClassOf"``, ``"Synonym"``, ``"Definition"``, ``"onProperty"``,
        ``"someValuesFrom"``, ``"type"``, ``"Replaced_by"``).
        - ``object`` (str): object value — a literal string, or a bare RID/blank node
        id when the object is a resource.
        - ``is_resource`` (bool): ``True`` if ``object`` is a URI/blank node
        reference rather than a literal value.
        - ``lang`` (str | None): the ``xml:lang`` tag for literal objects, if any.

        Returns:
            This parser instance, to support method chaining.

        Raises:
            RuntimeError: If called before :meth:`load`.
        """

        if self._graph is None:
            raise RuntimeError("load() must be called before parse()")

        rows: list[TripleRow] = []

        for subject, predicate, obj in self._graph:
            if isinstance(obj, rdflib.Literal):
                object_value = str(obj)
                is_resource = False
                lang = obj.language
            else:
                object_value = self._rid_from_uri(str(obj))
                is_resource = True
                lang = None

            rows.append(
                TripleRow(
                    subject=self._rid_from_uri(str(subject)),
                    predicate=self._rid_from_uri(str(predicate)),
                    object=object_value,
                    is_resource=is_resource,
                    lang=lang,
                )
            )

        self._triples = pa.Table.from_pylist([asdict(rows) for rows in rows])
        return self

    def save(self, output_path: Path) -> RadLexOwlParser:
        """Writes the parsed triples table to disk in a DuckDB-readable format.

        Args:
            output_path: Destination file path (e.g. a ``.parquet`` file) that
                downstream code can load with ``duckdb``'s Python module, either by
                querying the file directly or importing it into a persisted database.

        Returns:
            This parser instance, to support method chaining.

        Raises:
            RuntimeError: If called before :meth:`parse`.
            OSError: If ``output_path`` cannot be written.
        """

        if self._triples is None:
            raise RuntimeError("parse() must be called before save()")

        logger.info("Saving parsed triples to %s", output_path)
        pq.write_table(self._triples, output_path)

        return self

    @staticmethod
    def _rid_from_uri(uri: str) -> str:
        """Derives a bare RadLex RID from a full subject/resource URI.

        Handles both ``#``-fragment URIs (e.g. RDFS/OWL vocabulary terms like
        ``.../rdf-schema#subClassOf``) and ``/``-delimited URIs (e.g. RadLex terms
        like ``http://radlex.org/RID/RID1234``). Blank node identifiers, which
        contain neither separator, are returned unchanged.

        Args:
            uri: A subject, predicate, or resource URI from the ontology (e.g. an
                ``rdf:resource`` reference), or a blank node identifier string.

        Returns:
            The bare RID or local name string (e.g. ``"RID1234"``, ``"subClassOf"``),
            or the input unchanged if it contains no ``#`` or ``/``.
        """

        if "#" in uri:
            return uri.rsplit("#", 1)[-1]
        if "/" in uri:
            return uri.rsplit("/", 1)[-1]
        return uri
