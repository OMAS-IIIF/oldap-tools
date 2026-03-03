import requests
import typer
from rdflib import Dataset

#from oldap_tools.dump_project import log


def export_graphs_as_trig(
    graphdb_base: str,      # e.g. "http://localhost:7200"
    repo: str,              # e.g. "oldap"
    graph_iris: list[str],  # the 4 graphs you want
    auth: tuple[str, str] | None = None,
    timeout: int = 120,
) -> str:
    ds = Dataset()

    for g in graph_iris:
        # RDF4J "statements" endpoint; context must be given as <IRI>
        url = f"{graphdb_base.rstrip('/')}/repositories/{repo}/statements"
        params = {"context": f"<{g}>"}
        r = requests.get(
            url,
            params=params,
            headers={"Accept": "application/n-quads"},
            auth=auth,
            timeout=timeout,
        )
        if r.status_code != 200:
            #log.error(f"ERROR: Request to '{url}' failed with status code {r.status_code}")
            raise typer.Exit(code=1)

        # N-Quads keeps the graph/context in each statement -> perfect for Dataset
        ds.parse(data=r.text, format="nquads")

    trig = ds.serialize(format="trig")
    return trig.decode("utf-8") if isinstance(trig, bytes) else trig
