import requests
from requests.auth import HTTPDigestAuth
from rdflib import Graph

SPARQL_UPDATE = 'http://localhost:8890/sparql-auth'
AUTH = HTTPDigestAuth('dba', 'dba')


def load_ttl_into_graph(filepath, graph_uri):
    g = Graph()
    g.parse(filepath, format='turtle')

    triples = g.serialize(format='ntriples')

    r = requests.post(SPARQL_UPDATE,
                      data={'update': f'CLEAR GRAPH <{graph_uri}>'},
                      auth=AUTH)
    print(f'Clear <{graph_uri}>: {r.status_code}')

    lines = [l for l in triples.strip().split('\n') if l.strip()]
    batch_size = 100
    loaded = 0
    for i in range(0, len(lines), batch_size):
        batch = ' '.join(lines[i:i+batch_size])
        insert_q = f'INSERT DATA {{ GRAPH <{graph_uri}> {{ {batch} }} }}'
        r = requests.post(SPARQL_UPDATE, data={'update': insert_q}, auth=AUTH)
        if r.status_code not in (200, 201):
            print(f'Error at batch {i}: {r.status_code} {r.text[:200]}')
            return False
        loaded += len(lines[i:i+batch_size])
    print(f'Loaded {loaded} triples into <{graph_uri}>')
    return True


load_ttl_into_graph('data/Process_Anonymized.ttl', 'http://ex.org/ShapesGraph')
load_ttl_into_graph('data/validation_report.ttl', 'http://ex.org/ValidationReport')
load_ttl_into_graph('data/msg_0001.ttl', 'http://ex.org/DataGraph')

# Verify
r = requests.get('http://localhost:8890/sparql',
                 params={'query': 'SELECT ?g (COUNT(?s) as ?c) WHERE { GRAPH ?g { ?s ?p ?o } } GROUP BY ?g',
                         'format': 'application/sparql-results+json'},
                 auth=AUTH)
data = r.json()
for b in data['results']['bindings']:
    print(f"Graph: {b['g']['value']} => {b['c']['value']} triples")
