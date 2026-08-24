"""Tests for candidate-proposal validation and the search result contract.

These cover the guarantees a consumer relies on but which nothing else would notice
breaking: that a proposal cannot reference concepts the graph does not contain, and that
an empty result set has the same shape as a populated one.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import radlex_kg as kg

from res_radlex_parsing.graph.query import RadLexGraphQuery

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_valid_proposal_is_written(con, tmp_path):
    """A proposal whose anchors resolve should be appended verbatim."""
    out = tmp_path / "candidates.jsonl"
    record = kg.propose(
        con,
        name="left upper lobe micronodule",
        parent_rid="RID1327",
        rationale="Not modelled at this level of specificity.",
        relationships=[{"relation_type": "Part_Of", "target_rid": "RID1326"}],
        candidates_path=out,
    )
    written = json.loads(out.read_text().strip())
    assert written == record
    assert written["parent_rid"] == "RID1327"


def test_unknown_parent_rid_is_rejected(con, tmp_path):
    """An invented parent makes the candidate unplaceable, so it must not be written.

    Proposals are appended rather than rewritten, so a bad record stays in the review file
    until someone edits it by hand.
    """
    out = tmp_path / "candidates.jsonl"
    with pytest.raises(kg.ProposalError, match="not in the graph"):
        kg.propose(
            con,
            name="x",
            parent_rid="RID99999999",
            rationale="r",
            relationships=[],
            candidates_path=out,
        )
    assert not out.exists()


def test_unknown_relationship_target_is_rejected(con, tmp_path):
    """A relationship pointing at a non-existent concept must not be written."""
    out = tmp_path / "candidates.jsonl"
    with pytest.raises(kg.ProposalError, match="not in the graph"):
        kg.propose(
            con,
            name="x",
            parent_rid="RID1327",
            rationale="r",
            relationships=[{"relation_type": "Part_Of", "target_rid": "RID99999999"}],
            candidates_path=out,
        )
    assert not out.exists()


def test_misspelled_relation_type_is_rejected(con, tmp_path):
    """Relation types are checked against the ones RadLex actually uses.

    "PartOf" for "Part_Of" is the kind of near-miss that looks right in a proposal and is
    meaningless to anything consuming the file.
    """
    out = tmp_path / "candidates.jsonl"
    with pytest.raises(kg.ProposalError, match="not used by RadLex"):
        kg.propose(
            con,
            name="x",
            parent_rid="RID1327",
            rationale="r",
            relationships=[{"relation_type": "PartOf", "target_rid": "RID1326"}],
            candidates_path=out,
        )
    assert not out.exists()


@pytest.mark.parametrize(("name", "rationale"), [("", "r"), ("x", "   ")])
def test_blank_required_fields_are_rejected(con, tmp_path, name, rationale):
    """A candidate with no name or no rationale cannot be reviewed, so refuse it."""
    out = tmp_path / "candidates.jsonl"
    with pytest.raises(kg.ProposalError):
        kg.propose(
            con,
            name=name,
            parent_rid="RID1327",
            rationale=rationale,
            relationships=[],
            candidates_path=out,
        )


def test_empty_search_keeps_the_normal_schema(graph_path):
    """A query that normalizes to nothing must return the documented columns and types.

    Building the empty table from bare Python lists gives every column a null type, so
    callers that concatenate results or inspect the schema see a different shape from
    every non-empty result.
    """
    with RadLexGraphQuery(graph_path).load() as query:
        empty = query.search("---")
        populated = query.search("pleural effusion", limit=1)

    assert empty.num_rows == 0
    assert empty.schema == populated.schema


def test_script_paths_resolve_independently_of_cwd():
    """Default paths must anchor to the checkout, not the working directory.

    The skill is invoked from wherever the agent happens to be; a relative default made it
    report a missing graph and advise rebuilding one that already existed.
    """
    assert kg.DEFAULT_DB_PATH.is_absolute()
    assert kg.DEFAULT_CANDIDATES_PATH.is_absolute()
    assert kg.REPO_ROOT == REPO_ROOT
