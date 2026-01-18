import requests

query = """
SELECT DISTINCT ?uri 
FROM <http://ex.org/ValidationReport> 
WHERE { 
    ?s ?p ?uri . 
    FILTER(isURI(?uri) && CONTAINS(STR(?uri), "Steve"))
} 
LIMIT 20
"""

r = requests.get('http://localhost:8890/sparql', params={'query': query, 'format': 'json'})
results = r.json()['results']['bindings']
print(f"Found {len(results)} URIs containing 'Steve':")
for b in results:
    print(f"  - {b['uri']['value']}")
