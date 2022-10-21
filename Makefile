codemetapy:
	[ -e codemetapy ] || echo "ERROR: Please symlink the codemetapy repo dir manually!"

software.ttl:
	[ -e software.ttl ] || echo "ERROR: Please symlink software.ttl from https://github.com/CLARIAH/tool-discovery/blob/master/schemas/shacl/software.ttl manually."

test: codemetapy software.ttl
	codemetapy --enrich --validate software.ttl --baseuri http://localhost:8080/ codemetapy > /tmp/codemetapy.codemeta.json
	codemetapy --enrich --validate software.ttl --baseuri http://localhost:8080/ codemeta_server > /tmp/codemeta_server.codemeta.json
	codemetapy --enrich --validate software.ttl --baseuri http://localhost:8080/ codemetapy/tests/labirinto.package.json > /tmp/labirinto.codemeta.json
	codemetapy --enrich --validate software.ttl --baseuri http://localhost:8080/ codemetapy/tests/widoco.pom.xml > /tmp/widoco.codemeta.json
	codemetapy --enrich --validate software.ttl --baseuri http://localhost:8080/ codemetapy/tests/frog.codemeta.json > /tmp/frog.codemeta.json
	codemetapy  --baseuri http://localhost:8080/ --graph codemetapy/tests/frog.codemeta.json /tmp/labirinto.codemeta.json /tmp/widoco.codemeta.json /tmp/codemetapy.codemeta.json /tmp/codemeta_server.codemeta.json > /tmp/codemeta-server-graph.json
	codemeta-server --graph /tmp/codemeta-server-graph.json --host localhost --baseuri http://localhost:8080/ --baseurl http://localhost:8080/ --port 8080 --intro "Codemeta-server example" --includecontext --addcontext https://w3id.org/research-technology-readiness-levels
