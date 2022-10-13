codemetapy:
	[ -e codemetapy ] || echo "ERROR: Please symlink the codemetapy repo dir manually!"

test: codemetapy
	codemetapy codemetapy > /tmp/codemetapy.codemeta.json
	codemetapy codemeta_server > /tmp/codemeta_server.codemeta.json
	codemetapy codemetapy/tests/labirinto.package.json > /tmp/labirinto.codemeta.json
	codemetapy codemetapy/tests/widoco.pom.xml > /tmp/widoco.codemeta.json
	codemetapy --graph codemetapy/tests/frog.codemeta.json /tmp/labirinto.codemeta.json /tmp/widoco.codemeta.json /tmp/codemetapy.codemeta.json /tmp/codemeta_server.codemeta.json > /tmp/codemeta-server-graph.json
	codemeta-server --graph /tmp/codemeta-server-graph.json --host localhost --baseuri http://localhost:8080/ --baseurl http://localhost:8080/ --port 8080 --intro "Codemeta-server example"
