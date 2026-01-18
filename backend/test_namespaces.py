import requests
from collections import Counter

endpoint_url = "http://localhost:8890/sparql"
graph_uri = "http://ex.org/ValidationReport"

query = f"""
SELECT DISTINCT ?uri
FROM <{graph_uri}>
WHERE {{
  {{
    ?uri ?p ?o .
  }} UNION {{
    ?s ?uri ?o .
  }} UNION {{
    ?s ?p ?uri .
    FILTER(isURI(?uri))
  }}
}}
LIMIT 10000
"""

response = requests.get(
    endpoint_url,
    params={"query": query, "format": "json"},
    timeout=30
)
results = response.json()["results"]["bindings"]

discovered_namespaces = set()
for binding in results:
    if "uri" in binding:
        uri = binding["uri"]["value"]
        discovered_namespaces.add(uri)

# Extract namespace patterns
namespace_counts = Counter()
for uri in discovered_namespaces:
    if '#' in uri:
        namespace = uri.rsplit('#', 1)[0] + '#'
    elif '/' in uri:
        namespace = uri.rsplit('/', 1)[0] + '/'
    else:
        continue
    namespace_counts[namespace] += 1

# Show top 20 namespaces
print("Top 20 namespaces found:")
for namespace, count in namespace_counts.most_common(20):
    print(f"  {count:4d} - {namespace}")
