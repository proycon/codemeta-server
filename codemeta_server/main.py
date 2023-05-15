import sys
import os.path
import json
import traceback
import glob
import re
from typing import Union, Optional, List
from os import environ
from collections import defaultdict
from packaging.version import Version
from rdflib_endpoint import SparqlEndpoint
from rdflib import Graph, ConjunctiveGraph, URIRef, Literal
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from codemeta.codemeta import serialize
from codemeta.validation import get_validation_report
from codemeta.common import getstream, init_graph, AttribDict, SDO, RDF, CODEMETAPY, urijoin
from codemeta.parsers.jsonld import parse_jsonld
from codemeta2html import __path__ as CODEMETA2HTMLPATH
from codemeta2html.html import serialize_to_html
import argparse

VERSION = "0.4.0" #also adapt in setup.py and codemeta.json

STATIC_DIR = os.path.join(CODEMETA2HTMLPATH[0], "style")


SPARQL_BINDS = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <http://schema.org/>
PREFIX codemeta: <https://codemeta.github.io/terms/>
PREFIX stype: <https://w3id.org/software-types#>
PREFIX iodata: <https://w3id.org/software-iodata#>
PREFIX repostatus: <https://www.repostatus.org/#>
PREFIX trl: <https://w3id.org/research-technology-readiness-levels#>
PREFIX nwo: <https://w3id.org/nwo-research-fields#>
PREFIX tadirah: <https://vocabs.dariah.eu/tadirah/>
PREFIX spdx: <http://spdx.org/licences/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX orcid: <http://orcid.org/>
"""

NSPREFIXES = ('rdfs:', 'schema:','codemeta:','stype:','iodata:','repostatus:','trl:','nwo:','tadirah:','spdx:','skos:','dct:','orcid:')
    
class CodemetaServer(FastAPI):
    def __init__(self, *args,
                 graph: str,
                 title: str = "Codemeta Server",
                 description: str = "Serves software metadata using codemeta and schema.org\n[Source code](https://github.com/proycon/codemeta-server/)",
                 baseurl: str = "http://localhost:8080/",
                 baseuri: str = "",
                 version: str = VERSION,
                 includecontext: bool = False,
                 addcontext: list = [],
                 addcontextgraph: list = [],
                 **kwargs
                ) -> None:
        """Constructor for the CodemetaServer"""
        self.baseurl = baseurl
        if baseuri:
            self.baseuri = baseuri
        else:
            self.baseuri = self.baseurl

        if self.baseuri[-1] not in ('/','#','?'):
            self.baseuri += "/"
        if self.baseurl[-1] not in ('/','#','?'):
            self.baseurl += "/"

        self.title = kwargs.get('title')
        if kwargs.get('css'):
            self.css = [ x.strip() for x in kwargs.get('css',"").split(",") if x.strip() ]
        else:
            self.css = []

        self.intro = kwargs.get('intro',"")

        print(f"Instantiating codemeta server: graph={graph}, baseuri={self.baseuri}, baseurl={self.baseurl}",file=sys.stderr)

        self.includecontext = includecontext
        self.addcontext = addcontext
        self.addcontextgraph = addcontextgraph
        g, contextgraph = init_graph(self.get_args())
        parse_jsonld(g, None, getstream(graph), self.get_args())
        self.graph = g
        self.contextgraph = contextgraph
        if self.includecontext:
            self.graph += contextgraph #include context
        self.build_versionmap()
        if kwargs.get('inputlogdir'):
            self.read_logs(kwargs['inputlogdir'])
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
            public_url=urijoin(self.baseurl,"api/"),
            path="/",
            cors_enabled=True,
            example_query="""PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <http://schema.org/>
PREFIX codemeta: <https://codemeta.github.io/terms/>
PREFIX softwaretypes: <https://w3id.org/software-types#>
PREFIX softwareiodata: <https://w3id.org/software-iodata#>
PREFIX trl: <https://w3id.org/research-technology-readiness-levels#>
PREFIX repostatus: <https://www.repostatus.org/#>
PREFIX nwo: <https://w3id.org/nwo-research-fields#>
PREFIX tadirah: <https://vocabs.dariah.eu/tadirah/>
PREFIX spdx: <http://spdx.org/licenses/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?name ?description ?repo ?status ?license WHERE {
    ?sub schema:name ?name .
    ?sub rdf:type schema:SoftwareSourceCode .
    ?sub schema:license ?license .
    ?sub codemeta:developmentStatus ?status .
    ?sub schema:codeRepository ?repo .
} LIMIT 25
"""
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
        async def index(request: Request, res: Optional[str] = None, q: Optional[str] = None, sparql: Optional[str] = None):
            return self.get_index(request,res,q,sparql, "cardindex.html", )


        @self.get("/services/",
                  name="Services",
                  description="Provides a visualised index focused on software services",
                  responses= {
                      200: {
                          "description": "Service index",
                          "content": {
                              "text/html": {},
                          }
                      },
                  }
                )
        async def services(request: Request, res: Optional[str] = None, q: Optional[str] = None, sparql: Optional[str] = None):
            return self.get_index(request,res,q,sparql, "serviceindex.html", )

        @self.get("/table/",
                  name="Index",
                  description="Provides a tabular index to the data or simply returns all the data, i.e. the entire knowledge graph, depending on the content negotiation.",
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
        async def table(request: Request, res: Optional[str] = None, q: Optional[str] = None, sparql: Optional[str] = None):
            return self.get_index(request,res,q,sparql, "tableindex.html")

        @self.get("/data.json",
                  name="Full data download (JSON-LD)",
                  description="Returns all data as JSON-LD",
                  responses= {
                      200: {
                          "description": "Full dump of the knowledge graph",
                          "content": {
                              "application/json+ld": {},
                              "application/json": {},
                          }
                      },
                  }
                )
        async def data_json():
            return self.respond( "json",
                                 self.serialize(None, "json")
                               )

        @self.get("/data.ttl",
                  name="Full data download (Turtle)",
                  description="Returns all data as Turtle",
                  responses= {
                      200: {
                          "description": "Full dump of the knowledge graph",
                          "content": {
                              "text/turtle": {},
                          }
                      },
                  }
                )
        async def data_turtle():
            return self.respond( "turtle",
                                 self.serialize(None, "turtle")
                               )

        @self.get("/validation/{resource:path}",
                  name="Validation report",
                  description="Returns a specific validation log",
                  responses= {
                      200: {
                          "description": "Visualisation validation log",
                          "content": {
                              "text/plain": {},
                          }
                      },
                  }
                 )
        async def get_validation(resource: str, request: Request):
            res = URIRef(urijoin(self.baseuri, "validation", resource))
            if (res,None,None) in self.graph:
                return self.respond( "text",
                             get_validation_report(self.graph, res)
                            )
            else:
                return self.respond404("text")

        @self.get("/{resource:path}",
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
        @self.get("/{resource:path}/",
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
            if resource.endswith("data.json"):
                resource = resource[:-(len("data.json") + 1)]
                output_type = "json"
            elif resource.endswith("data.ttl"):
                resource = resource[:-(len("data.ttl") + 1)]
                output_type = "ttl"
            elif resource.endswith(".json"):
                resource = resource[:-5]
                output_type = "json"
            elif resource.endswith(".ttl"):
                resource = resource[:-4]
                output_type = "ttl"
            else:
                output_type = self.get_output_type(request)
            res = URIRef(urijoin(self.baseuri, resource))
            if (res,None,None) in self.graph:
                return self.respond( output_type,
                             self.serialize(res, output_type)
                            )
            else:
                #if the resource does not exist, a version qualifier may be missing, attempt to find the latest version
                versions = self.versionmap.get(resource.strip("/"),[])
                if versions:
                    res = URIRef(urijoin(self.baseuri, resource,versions[0])) #first version is the latest one
                    if (res,None,None) in self.graph:
                        return self.respond( output_type,
                                     self.serialize(res, output_type)
                                    )
            return self.respond404(output_type)




    def serialize(self, res: Union[Optional[URIRef],List[URIRef]], output_type: str, **kwargs) -> str:
        if output_type == "html":
             return serialize_to_html(self.graph, res, self.get_args(output_type), contextgraph=self.contextgraph, title=self.title, **kwargs )
        else:
             return serialize(self.graph, res, self.get_args(output_type), contextgraph=self.contextgraph, title=self.title, **kwargs )


    def get_index(self, request: Request, res: Optional[str] = None, q: Optional[str] = None, sparql: Optional[str] = None, indextemplate: str  = "cardindex.html"):
        output_type = self.get_output_type(request)
        if q:
            sparql = self.formulate_query(q)
        if res: res = [ URIRef(self.baseuri + x) for x in res.split(";") ]
        try:
            response = self.serialize(res, output_type, sparql_query=sparql, indextemplate=indextemplate, q=q if q else "")
        except Exception as e:
            msg = str(e)
            if sparql: msg += f"<pre>SPARQL query was: {sparql}\n</pre>"
            exc_type, exc_value, exc_traceback = sys.exc_info()
            msg += "<pre>" + "\n".join(traceback.format_exception(exc_type, exc_value, exc_traceback)) + "</pre>"
            print(msg,file=sys.stderr)
            return self.respond400( output_type, msg)
        return self.respond( output_type, response)

    def get_args(self, output_type: str = "json") -> AttribDict:
        return AttribDict({
            "baseuri": self.baseuri,
            "baseurl": self.baseurl,
            "styledir": "static",
            "graph": True,
            "output": output_type,
            "buildsite": True,
            "serverside": True,
            "no_cache": False,
            "includecontext": self.includecontext,
            "addcontext": self.addcontext,
            "addcontextgraph": self.addcontextgraph,
            "intro": self.intro,
            "css": [ f"codemeta.css?v={VERSION}" , f"fontawesome.css?v={VERSION}" ] + self.css #cache busting
        })

    def respond(self, output_type: str, content: Union[str,bytes, None]) -> Response:
        if content is None: content = ""
        if output_type == 'json':
            return Response( content=content, media_type="application/json+ld")
        elif output_type == "turtle":
            return Response( content=content, media_type="text/turtle")
        elif output_type == "html":
            return Response( content=content, media_type="text/html")
        return Response( content=content, media_type="text/plain")

    def respond404(self, output_type: str) -> Response:
        if output_type == 'json':
            return Response(status_code=404, content='{"message": "Resource not found" }', media_type="application/json")
        elif output_type == "turtle":
            return Response(status_code=404, content="", media_type="text/turtle")
        elif output_type == "html":
            return Response(status_code=404, content="<html><body><strong>404</strong> - Not Found - Resource does not exist</body></html>", media_type="text/html")
        return Response(status_code=404, content="404 Not Found - Resource does not exist", media_type="text/plain")

    def respond400(self, output_type: str, message: str) -> Response:
        if output_type == 'json':
            return Response(status_code=400, content=json.dumps({"message": message}), media_type="application/json")
        elif output_type == "turtle":
            return Response(status_code=400, content="", media_type="text/turtle")
        elif output_type == "html":
            return Response(status_code=400, content=f"<html><body><strong>400</strong> - Bad Request - {message}</body></html>", media_type="text/html")
        return Response(status_code=400, content=f"400 Bad Request - {message}", media_type="text/plain")

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

    def formulate_query(self, q: str, restype="schema:SoftwareSourceCode"):
        """Translate a query from a simpler less-formalised syntax to SPARQL"""
        conditions = []
        for clause in q.split(';'): #semicolon splits queries (conjunctive)
            if clause.find('=') > 0:
                key, value = clause.split('=',1)
                value = value.strip()
                if value and value[0] == '=': #== operator for exact match
                    value = value[1:]
                    exact = True
                else:
                    exact = False
                if value.find('|') > 0:
                    values = []
                    for value in value.split('|'): #disjunction
                        if not (value.startswith(NSPREFIXES) or value.isnumeric()):
                            value = f"\"{value}\"" #string literal
                        values.append(f"{value} .")
                    if values:
                        i = len(conditions) + 1
                        conditions.append("{{ VALUES ?values{i} {{ " + ", ".join(values)  + f" }} ?res {key} ?values{i}.")
                else:
                    if not (value.startswith(NSPREFIXES) or value.isnumeric()):
                        value = f"\"{value}\"" #string literal
                    i = len(conditions) + 1
                    if exact:
                        conditions.append(f"?res {key} {value} .")
                    else:
                        conditions.append(f"?res {key} ?v{i} FILTER regex(str(?v{i}), {value}, \"i\") .") #last i is for case-insensitive
            else:
                value = clause.strip()
                i = len(conditions) + 1
                #broad search on names, descriptions and keywords
                conditions.append(f"{{ ?res schema:name ?v{i}a FILTER regex(str(?v{i}a), \"{value}\", \"i\") . }} UNION {{ ?res schema:description ?v{i}b FILTER regex(str(?v{i}b), \"{value}\", \"i\") . }} UNION {{ ?res schema:keywords ?v{i}c FILTER regex(str(?v{i}c), \"{value}\", \"i\") . }}")

        conditions = "\n".join(conditions)

        return f"""
        {SPARQL_BINDS}
        SELECT DISTINCT ?res
        WHERE {{
            ?res rdf:type {restype} .
            {conditions}
        }}
        """

    def read_logs(self, inputlogdir: str):
        """Add information from the logs directly to the graph using an internal namespace"""
        for logfile in glob.glob(os.path.join(inputlogdir,"*.harvest.log")):
            identifier = os.path.basename(logfile).split(".")[0]
            res = URIRef(self.baseuri + identifier)
            if not (res,RDF.type,SDO.SoftwareSourceCode) in self.graph:
                versions = self.versionmap.get(identifier,[])
                if versions:
                    res = URIRef(urijoin(self.baseuri, identifier,versions[0])) #first version is the latest one
                    if not (res,RDF.type,SDO.SoftwareSourceCode) in self.graph:
                        print(f"Log {logfile} describes non-existing resource {res}",file=sys.stderr)
                        return
            errors = 0
            with open(logfile,'r',encoding='utf-8') as f:
                logdata = f.readlines()
                for line in logdata:
                    if line.lower().find("harvester error") != -1:
                        errors += 1
                self.graph.set((res, CODEMETAPY.errors, Literal(errors)))
                self.graph.set((res, CODEMETAPY.log, Literal("\n".join(logdata))))

    def build_versionmap(self):
        self.versionmap = defaultdict(list)
        for s,_,_ in self.graph.triples((None,RDF.type,SDO.SoftwareSourceCode)):
            if str(s).startswith(self.baseuri):
                components = str(s)[len(self.baseuri):].strip("/").split("/")
                if len(components) == 2:
                    name, version = components
                    print(f"Versionmap: adding SofwareSourceCode {name} with version {version}",file=sys.stderr)
                    self.versionmap[name].append(version)
        targetproducts = set()
        for _,_, o in self.graph.triples((None,SDO.targetProduct,None)):
            if str(o).startswith(self.baseuri) and o not in targetproducts:
                targetproducts.add(o) #prevents duplicates
                components = str(o)[len(self.baseuri):].strip("/").split("/")
                if len(components) == 3:
                    interfacetype, name, version = components
                    print(f"Versionmap: adding {interfacetype} {name} with version {version}",file=sys.stderr)
                    self.versionmap[interfacetype + "/" + name].append(version)
        
        for key, versions in self.versionmap.items():
            self.versionmap[key] = sorted(versions, key=lambda x: Version(re.sub("^v","", x))._key if validversion(x) else (9999,0,0,0,0,0), reverse=True)

def validversion(s: str) -> bool:
    try:
        Version(s)
        return True
    except:
        return False

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
    if not kwargs.get('title'):
        if 'CODEMETA_TITLE' in environ:
            kwargs['title'] = environ['CODEMETA_TITLE']
    if not kwargs.get('title'):
        kwargs['title'] = "Codemeta server" #we must have a title

    if not kwargs.get('intro'):
        if 'CODEMETA_INTRO' in environ:
            kwargs['intro'] = environ['CODEMETA_INTRO']

    if not kwargs.get('baseurl'):
        kwargs['baseurl'] = kwargs['baseuri']

    if not kwargs.get('inputlogdir'):
        if 'CODEMETA_INPUTLOGDIR' in environ:
            kwargs['inputlogdir'] = environ['CODEMETA_INPUTLOGDIR']

    if not kwargs.get('css'):
        if 'CODEMETA_CSS' in environ:
            kwargs['css'] = environ['CODEMETA_CSS']

    if not kwargs.get('addcontext'):
        if 'CODEMETA_ADDCONTEXT' in environ:
            kwargs['addcontext'] = environ['CODEMETA_ADDCONTEXT'].split(" ")

    if not kwargs.get('addcontextgraph'):
        if 'CODEMETA_ADDCONTEXTGRAPH' in environ:
            kwargs['addcontextgraph'] = environ['CODEMETA_ADDCONTEXTGRAPH'].split(" ")

    if not kwargs.get('includecontext'):
        if 'CODEMETA_INCLUDECONTEXT' in environ:
            kwargs['includecontext'] = environ['CODEMETA_INCLUDECONTEXT'].lower() in ("true","yes","1")

    return CodemetaServer(**kwargs)


def main():
    import uvicorn
    parser = argparse.ArgumentParser(description="Codemeta Server", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--host',type=str, help="Host to serve on", action='store', default="0.0.0.0")
    parser.add_argument('--port',type=int, help="Port to serve on", action='store', default=8080)
    parser.add_argument('--graph',type=str, help="JSON-LD graph to load (as produced by codemetapy --graph)", action='store', required=True)
    parser.add_argument('--baseuri',type=str, help="Base URI used in the IDs of all resources", action='store', required=True)
    parser.add_argument('--baseurl',type=str, help="Base URL", action='store')
    parser.add_argument('--inputlogdir',type=str, help="Directory where *.harvest.log can be found as generated by codemeta-harvester", action='store')
    parser.add_argument('--addcontext', help="Add the specified jsonld (must be a URL) to the context (and to the context graph). May be specified multiple times.", action='append',required=False)
    parser.add_argument('--includecontext', help="Include all context vocabularies in the main graph and express it verbosely in serialisations. This makes the resoluting codemeta.json richer without the need to query certain external vocabularies, at the cost of added redundancy.", action='store_true',required=False)
    parser.add_argument('--intro', type=str, help="Introductory text (html) to add to indices", action='store',required=False)
    parser.add_argument('--title',type=str, help="Title", action='store')
    parser.add_argument('--css',type=str, help="URLs to extra CSS stylesheets to use (comma separated list)", action='store')
    args = parser.parse_args() #parsed arguments can be accessed as attributes

    # Start the SPARQL endpoint based on the RDFLib Graph
    app = get_app(**args.__dict__)
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
