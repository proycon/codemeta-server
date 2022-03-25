import sys
import os.path
from typing import Union
from os import environ
from rdflib_endpoint import SparqlEndpoint
from rdflib import Graph, ConjunctiveGraph, URIRef
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from codemeta import __path__ as CODEMETAPATH
from codemeta.codemeta import serialize
from codemeta.common import getstream, init_graph, AttribDict
from codemeta.parsers.jsonld import parse_jsonld
import argparse

VERSION = "0.1"

STATIC_DIR = os.path.join(CODEMETAPATH[0], "resources")

class CodemetaServer(FastAPI):
    def __init__(self, *args,
                 graph: str,
                 title: str = "Codemeta Server",
                 description: str = "Serves software metadata using codemeta and schema.org\n[Source code](https://github.com/proycon/codemeta-server/)",
                 baseurl: str = "http://localhost:8080",
                 baseuri: str = "",
                 version: str = VERSION,
                 **kwargs
                ) -> None:
        """Constructor for the CodemetaServer"""
        self.baseurl = baseurl
        if baseuri:
            self.baseuri = baseuri
        else:
            self.baseuri = self.baseurl

        print(f"Instantiating codemeta server: graph={graph}, baseuri={self.baseuri}, baseurl={self.baseurl}",file=sys.stderr)

        g, contextgraph = init_graph()
        parse_jsonld(g, None, getstream(graph), args)
        self.graph = g
        self.contextgraph = contextgraph
        # Instantiate FastAPI
        super().__init__(
            title=title, description=description, version=version,
        )

        #Instantiate sub API for SPARQL endpoint
        subapi = SparqlEndpoint(
            graph=self.graph,
            title="Codemeta Server SPARQL endpoint",
            description="A SPARQL endpoint to serve software metadata using codemeta and schema.org\n[Source code](https://github.com/proycon/codemeta-server/)",
            version=VERSION,
            public_url=f"{self.baseurl}/api/sparql",
            cors_enabled=True,
        )
        self.mount("/api", subapi)

        #Serve static files
        self.mount("/static", StaticFiles(directory=STATIC_DIR))

        @self.get("/",
                  name="Index",
                  description="Provides an index to the data or simply returns all the data, i.e. the entire knowledge graph, depending on the content negotiation.",
                  responses= {
                      200: {
                          "description": "Index to the data or full dump of the knowledge graph",
                          "content": {
                              "text/html": {},
                              "application/json+ld": {},
                              "application/json": {},
                              "text/turtle": {},
                          }
                      },
                  }
                )
        async def index(request: Request):
            output_type = self.get_output_type(request)
            return self.respond( output_type,
                                  serialize(self.graph, None, self.get_args(output_type), contextgraph=self.contextgraph )
                               )

        @self.get("/{resource: path}",
                  name="Resource",
                  description="Returns the selected resource",
                  responses= {
                      200: {
                          "description": "Visualisation of the resource (html) or the linked data of the resource (json-ld/turtle)",
                          "content": {
                              "text/html": {},
                              "application/json+ld": {},
                              "application/json": {},
                              "text/turtle": {},
                          }
                      },
                  }
                 )
        async def get_resource(resource: str, request: Request):
            output_type = self.get_output_type(request)
            res = URIRef(os.path.join(self.baseuri, resource))
            if (res,None,None) in self.graph:
                self.respond( output_type,
                             serialize(self.graph, res, self.get_args(output_type), contextgraph=self.contextgraph )
                            )
            else:
                return self.respond404(output_type)


    def get_args(self, output_type: str) -> AttribDict:
        return AttribDict({
            "baseuri": self.baseuri,
            "graph": True,
            "output": output_type,
            "toolstore": True,
            "css": [ os.path.join(self.baseurl,"static/codemeta.css") , os.path.join(self.baseurl,"static/fontawesome.css") ]
        })

    def respond(self, output_type: str, content: Union[str,bytes, None]) -> Response:
        if content is None: content = ""
        if output_type == 'json':
            return Response( content=content, media_type="application/json+ld")
        elif output_type == "turtle":
            return Response( content=content, media_type="text/turtle")
        elif output_type == "html":
            return Response( content=content, media_type="text/html")

    def respond404(self, output_type: str) -> Response:
        if output_type == 'json':
            return Response(status_code=404, content='{"message": "Resource not found" }', media_type="application/json")
        elif output_type == "turtle":
            return Response(status_code=404, content="", media_type="text/turtle")
        elif output_type == "html":
            return Response(status_code=404, content="<html><body><strong>404</strong> - Not Found - Resource does not exist</body></html>", media_type="text/html")

    def get_output_type(self, request: Request) -> str:
        """Get the outputtype based on content negotiation"""
        accept = request.headers.get('Accept')
        if accept:
            accept = accept.split(",")
            ordered = []
            for item in accept:
                item = item.split(";")
                q = 1.0
                if len(item) > 1:
                    if item[1].startswith("q="):
                        try:
                            q = float(item[1][2:])
                        except ValueError:
                            q = 1.0
                ordered.append( (item[0],q) )

            #sort by q value
            ordered.sort(key=lambda x: -1 * x[1])

            for item, _q in ordered:
                if item.find("html") != -1:
                    return "html"
                elif item.find("json") != -1:
                    return "json"
                elif item.find("turtle") != -1:
                    return "turtle"
                elif item.find("rdf+") or item.find("text/n3"):
                    #For a bunch of RDF types which we don't support, we just return turtle instead
                    return "turtle"
        return "html"

def get_app(**kwargs):
    if not kwargs.get('graph'):
        if 'CODEMETA_GRAPH' in environ:
            kwargs['graph'] = environ['CODEMETA_GRAPH']
        else:
            raise Exception("No input data provided, use --graph or set environment variable $CODEMETA_GRAPH (to a JSON-LD file that is the output of codemeta --graph)")
    if not kwargs.get('baseuri'):
        if 'CODEMETA_BASEURI' in environ:
            kwargs['baseuri'] = environ['CODEMETA_BASEURI']
        else:
            raise Exception("No base URI provided, use --baseuri or set environment variable $CODEMETA_BASEURI")

    if not kwargs.get('baseurl'):
        kwargs['baseurl'] = kwargs['baseuri']

    return CodemetaServer(
        graph=kwargs['graph'],
        baseuri=kwargs['baseuri'],
        baseurl=kwargs['baseurl'],
    )

def main():
    import uvicorn
    parser = argparse.ArgumentParser(description="Codemeta Server", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--host',type=str, help="Host to serve on", action='store', default="0.0.0.0")
    parser.add_argument('--port',type=int, help="Port to serve on", action='store', default=8080)
    parser.add_argument('--graph',type=str, help="JSON-LD graph to load (as produced by codemetapy --graph)", action='store', required=True)
    parser.add_argument('--baseuri',type=str, help="Base URI used in the IDs of all resources", action='store', required=True)
    parser.add_argument('--baseurl',type=str, help="Base URL (only needed when distinct from base URI)", action='store')
    args = parser.parse_args() #parsed arguments can be accessed as attributes

    # Start the SPARQL endpoint based on the RDFLib Graph
    app = get_app(**args.__dict__)
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
