codemetapy:
	[ -e codemetapy ] || echo "ERROR: Please symlink the codemetapy repo dir manually!"

test: codemetapy
	codemetapy --baseuri http://localhost:8080/ codemetapy > /tmp/codemetapy.codemeta.json
	codemetapy --baseuri http://localhost:8080/ codemeta_server > /tmp/codemeta_server.codemeta.json
	codemetapy --baseuri http://localhost:8080/ codemetapy/tests/labirinto.package.json > /tmp/labirinto.codemeta.json
	codemetapy --baseuri http://localhost:8080/ codemetapy/tests/widoco.pom.xml > /tmp/widoco.codemeta.json
	codemetapy --baseuri http://localhost:8080/ --graph codemetapy/tests/frog.codemeta.json /tmp/labirinto.codemeta.json /tmp/widoco.codemeta.json /tmp/codemetapy.codemeta.json /tmp/codemeta_server.codemeta.json > /tmp/codemeta-server-graph.json
	codemeta-server --graph /tmp/codemeta-server-graph.json --host localhost --baseuri http://localhost:8080/ --baseurl http://localhost:8080/ --port 8080 --intro "Codemeta-server example"
