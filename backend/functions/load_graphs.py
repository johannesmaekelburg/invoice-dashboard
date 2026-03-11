"""
Utility to load RDF graphs into Virtuoso.
Can be run directly: python backend/functions/load_graphs.py [data_ttl]

Usage:
    python backend/functions/load_graphs.py                  # uses default data/msg_0001.ttl
    python backend/functions/load_graphs.py data/msg_0014.ttl
"""
import sys
import os
import requests
from requests.auth import HTTPDigestAuth
from rdflib import Graph

# Resolve paths relative to the project root regardless of cwd
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

SPARQL_UPDATE = 'http://localhost:8890/sparql-auth'
AUTH = HTTPDigestAuth('dba', 'dba')

SHAPES_GRAPH_URI = 'http://ex.org/ShapesGraph'
VALIDATION_REPORT_URI = 'http://ex.org/ValidationReport'
DATA_GRAPH_URI = 'http://ex.org/DataGraph'


def _abs(relative_path):
    return os.path.join(PROJECT_ROOT, relative_path)


def load_ttl_into_graph(filepath, graph_uri, skolemize=False):
    """Parse a TTL file and load it into a named Virtuoso graph."""
    g = Graph()
    g.parse(filepath, format='turtle')
    if skolemize:
        g = g.skolemize()
    print(f'  {len(g)} triples (skolemized={skolemize})')

    triples = g.serialize(format='ntriples')
    lines = [l for l in triples.strip().split('\n') if l.strip()]

    r = requests.post(SPARQL_UPDATE,
                      data={'update': f'CLEAR GRAPH <{graph_uri}>'},
                      auth=AUTH)
    print(f'  CLEAR <{graph_uri}>: {r.status_code}')

    batch_size = 100
    loaded = 0
    for i in range(0, len(lines), batch_size):
        batch = ' '.join(lines[i:i + batch_size])
        insert_q = f'INSERT DATA {{ GRAPH <{graph_uri}> {{ {batch} }} }}'
        r = requests.post(SPARQL_UPDATE, data={'update': insert_q}, auth=AUTH)
        if r.status_code not in (200, 201):
            print(f'  Error at batch {i}: {r.status_code} {r.text[:200]}')
            return False
        loaded += len(lines[i:i + batch_size])

    print(f'  Loaded {loaded} triples into <{graph_uri}>')
    return True


def generate_and_load(data_ttl_path):
    """
    Full pipeline:
      1. Load shapes graph
      2. Validate data TTL against shapes → produce validation report
      3. Skolemize + load validation report (avoids blank-node scoping bug)
      4. Load data graph
      5. Print triple counts
    """
    import pyshacl

    shapes_path = _abs('data/Process_Anonymized.ttl')

    print(f'\n=== Loading shapes graph ===')
    load_ttl_into_graph(shapes_path, SHAPES_GRAPH_URI)

    print(f'\n=== Validating {data_ttl_path} against SHACL shapes ===')
    import rdflib
    _, g_report, _ = pyshacl.validate(
        data_ttl_path,
        shacl_graph=shapes_path,
        data_graph_format='turtle',
        shacl_graph_format='turtle',
    )
    report_path = _abs('data/validation_report.ttl')
    g_report.serialize(report_path, format='turtle')
    violation_count = sum(1 for _ in g_report.subjects(
        rdflib.RDF.type,
        rdflib.URIRef('http://www.w3.org/ns/shacl#ValidationResult')
    ))
    print(f'  {violation_count} violations found, saved to {report_path}')

    print(f'\n=== Loading validation report (skolemized) ===')
    load_ttl_into_graph(report_path, VALIDATION_REPORT_URI, skolemize=True)

    print(f'\n=== Loading data graph ===')
    load_ttl_into_graph(data_ttl_path, DATA_GRAPH_URI)

    print(f'\n=== Triple counts ===')
    r = requests.post('http://localhost:8890/sparql',
                      data={'query': 'SELECT ?g (COUNT(?s) AS ?c) WHERE { GRAPH ?g { ?s ?p ?o } } GROUP BY ?g',
                            'format': 'application/sparql-results+json'})
    for b in r.json()['results']['bindings']:
        print(f'  {b["g"]["value"]}  →  {b["c"]["value"]} triples')


if __name__ == '__main__':
    data_ttl = sys.argv[1] if len(sys.argv) > 1 else 'data/msg_0001.ttl'
    data_ttl = _abs(data_ttl) if not os.path.isabs(data_ttl) else data_ttl
    generate_and_load(data_ttl)
