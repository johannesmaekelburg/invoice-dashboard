"""
Skolemize the SHACL validation report and reload it into Virtuoso.

Blank nodes in N-triples are scoped per INSERT DATA statement, so when the
graph was loaded in batches, each bnode became a different node — breaking
multi-predicate SPARQL joins. Skolemization converts every blank node to a
stable IRI so joins work correctly.
"""
import requests
from requests.auth import HTTPDigestAuth
from rdflib import Graph

SPARQL_UPDATE = 'http://localhost:8890/sparql-auth'
GRAPH_URI = 'http://ex.org/ValidationReport'
AUTH = HTTPDigestAuth('dba', 'dba')

INPUT_TTL = 'data/validation_report.ttl'
OUTPUT_TTL = 'data/validation_report_skolemized.ttl'

# --- Skolemize ---
print(f'Parsing {INPUT_TTL} ...')
g = Graph()
g.parse(INPUT_TTL, format='turtle')
print(f'  {len(g)} triples before skolemization')

g_sk = g.skolemize()
print(f'  {len(g_sk)} triples after skolemization')

g_sk.serialize(OUTPUT_TTL, format='turtle')
print(f'Saved skolemized graph to {OUTPUT_TTL}')

# --- Reload into Virtuoso ---
triples = g_sk.serialize(format='ntriples')
lines = [l for l in triples.strip().split('\n') if l.strip()]
print(f'  {len(lines)} N-triple lines to load')

# Clear existing graph
r = requests.post(SPARQL_UPDATE,
                  data={'update': f'CLEAR GRAPH <{GRAPH_URI}>'},
                  auth=AUTH)
print(f'CLEAR <{GRAPH_URI}>: {r.status_code}')

# Load in batches (blank nodes are now IRIs — no scoping issue)
batch_size = 100
loaded = 0
errors = 0
for i in range(0, len(lines), batch_size):
    batch = ' '.join(lines[i:i + batch_size])
    insert_q = f'INSERT DATA {{ GRAPH <{GRAPH_URI}> {{ {batch} }} }}'
    r = requests.post(SPARQL_UPDATE, data={'update': insert_q}, auth=AUTH)
    if r.status_code not in (200, 201):
        print(f'  Error at batch {i}: {r.status_code} {r.text[:200]}')
        errors += 1
    else:
        loaded += len(lines[i:i + batch_size])

print(f'Loaded {loaded} triples ({errors} batch errors)')

# --- Verify ---
verify_q = (f'SELECT (COUNT(?v) AS ?c) (COUNT(DISTINCT ?fn) AS ?nodes) '
            f'FROM <{GRAPH_URI}> WHERE {{ '
            f'?v a <http://www.w3.org/ns/shacl#ValidationResult> . '
            f'?v <http://www.w3.org/ns/shacl#focusNode> ?fn }}')
r = requests.post('http://localhost:8890/sparql',
                  data={'query': verify_q,
                        'format': 'application/sparql-results+json'})
data = r.json()
b = data['results']['bindings'][0]
print(f'Verification: {b["c"]["value"]} ValidationResults, '
      f'{b["nodes"]["value"]} distinct focus nodes')
