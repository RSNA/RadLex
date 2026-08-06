import marimo

__generated_with = "0.23.15"
app = marimo.App(width="medium")


@app.cell
def _():
    from pathlib import Path

    from res_radlex_parsing.graph.build_graph import RadLexGraphBuilder
    from res_radlex_parsing.graph.query import RadLexGraphQuery
    from res_radlex_parsing.owl_ingest.parse import RadLexOwlParser

    return Path, RadLexGraphBuilder, RadLexGraphQuery, RadLexOwlParser


@app.cell
def _(Path):
    owl_path = Path("data/staging/RadLex.owl")
    triples_path = Path("data/intermediate/radlex_triples.parquet")
    db_path = Path("data/intermediate/radlex.duckdb")
    return db_path, owl_path, triples_path


@app.cell
def _(RadLexOwlParser, owl_path):
    parser = RadLexOwlParser(owl_path)
    return (parser,)


@app.cell
def _(parser, triples_path):
    parser.load().parse().save(triples_path)
    return


@app.cell
def _(parser):
    parser._triples
    return


@app.cell
def _(RadLexGraphBuilder, db_path, triples_path):
    builder = RadLexGraphBuilder(triples_path, db_path)
    return (builder,)


@app.cell
def _(builder):
    builder.load()
    return


@app.cell
def _(builder):
    builder.build()
    return


@app.cell
def _(builder):
    builder.save()
    return


@app.cell
def _(builder):
    builder._graph.number_of_nodes(), builder._graph.number_of_edges()
    return


@app.cell
def _(builder):
    next(iter(builder._graph.nodes(data=True)))
    return


@app.cell
def _(RadLexGraphQuery, db_path):
    query = RadLexGraphQuery(db_path).load()
    return (query,)


@app.cell
def _(query):
    query.search("pulmonary nodule")
    return


@app.cell
def _(query):
    query.get_node("RID1327")
    return


@app.cell
def _(query):
    query.get_parents("RID1327")
    return


@app.cell
def _(query):
    query.get_children("RID1327")
    return


if __name__ == "__main__":
    app.run()
