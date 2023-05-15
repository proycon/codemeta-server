[![Project Status: Active -- The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
[![Latest release in the Python Package Index](https://img.shields.io/pypi/v/codemeta-server)](https://pypi.org/project/codemeta-server/)

# Codemeta Server

Codemeta server provides a simple portal to software tools, based on software
metadata in [codemeta](https://codemeta.github.io) and
[schema.org](https://schema.org). It is implemented as an in-memory RDF triple
store and provides an API (including SPARQL endpoint) for querying. It builds
upon the [codemeta2html](http://github.com/proycon/codemeta2html) and
[codemetapy](http://github.com/proycon/codemetapy) libraries, which implement
most of the functionality. Automatic harvesting of software metadata can be
accomplished via
[codemeta-harvester](https://github.com/proycon/codemeta-harvester).

**Note:** If you want a static site instead of a triple-store backed web application, then 
you dont need codemeta-server and can just use [codemeta2html](http://github.com/proycon/codemeta2html).

Features:

* Web-user interface for end-users (i.e. everything from [codemeta2html](http://github.com/proycon/codemeta2html)):
    * rich [RDFa](https://www.w3.org/TR/rdfa-primer/) data (codemeta/schema.org/etc) embedded in the HTML,
      expressing as much of the input linked data as possible. This means though we visualise for humans, we do 
      not sacrifice on machine parsability and semantic interpretability.
    * index pages (card view & table view)
    * one dedicated page per software source project
    * client-side filtering (faceted search) capabilities
    * direct access to the underlying JSON-LD and Turtle serialisations per source project and for the complete data graph as a whole
    * responsive layout suitable for different devices and screen-sizes
    * Integrates some badges (aka shields) like for GitHub, Repostatus
    * minimal amount of external web calls (only for github/gitlab badges and for external resources references directly by the software metadata itself)
    * minimal client-side javascript, also usable without (except for filtering)
* Simple server-side search/query facilities
* Advanced query facilities using SPARQL:
    * SPARQL endpoint
    * [YASGUI](https://github.com/TriplyDB/YASGUI) front-end for end-users.
* JSON-LD and turtle serialisations for all data, full support for content negotiation
* Supports various extensions to codemeta:
    * [Software Types and Services](https://github.com/proycon/codemetapy#software-types-and-services)

This software is developed in the scope of the [CLARIAH-PLUS project](https://clariah.nl), a
`Dockerfile`  for the CLARIAH Tool Discovery pipeline, including both the
harvester and this server and API powering the CLARIAH Tool Store, can be found
here: https://github.com/CLARIAH/tool-discovery .

## Installation

`pip install codemeta-server`

## Usage

In development scenarios, you can run `codemeta-server` as follows:
`
codemeta-server --graph data.json --baseuri http://localhost:8080/ --baseurl http://localhost:8080/ --port 8080
`
Check ``codemeta-server --help`` for help on all the options.

The file `data.json` is produced by [codemetapy](https://github.com/proycon/codemetapy) (possibly via [codemeta-harvester](https://github.com/proycon/codemeta-harvester) and contains the full linked data graph of all tools you want to show.
Say you have ``codemeta.json`` files for  two resources, then you can use codemetapy to create a graph as follows:

``
codemetapy --baseuri http://localhost:8080/ --graph resource1.codemeta.json resource2.codemeta.json > data.json
``

If you have no codemeta files at all yet, then still you can use codemetapy (via
[codemeta-harvester](https://github.com/proycon/codemeta-harvester) to automatically extract metadata from other known schemas.

For production scenarios, you'll want to run codemeta-server via WSGI/ASGI, check the Dockerfile in https://github.com/CLARIAH/tool-discovery .

## Screenshots

Excerpt of a tool index in the default 'card' view:

![Index - card view](screenshot_index_cards.jpg)

Excerpt of a tool index in the table view:

![Index - table view](screenshot_index_table.jpg)

An example page for a specific tool:

![Tool page](screenshot_page.jpg)

The SPARQL frontend (Yasgui):

![SPARQL frontend](screenshot_sparql.jpg)
