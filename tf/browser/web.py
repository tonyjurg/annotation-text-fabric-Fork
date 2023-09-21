"""
# Web interface

## About

TF contains a web interface
in which you can enter a search template and view the results.

This is realized by a web app based on
[Flask](http://flask.pocoo.org/docs/1.0/).

This web app initializes by loading a TF corpus from which it obtains data.
In repsonse to requests, it merges the retrieved data into a set of
[templates](https://github.com/annotation/text-fabric/tree/master/tf/browser/views).

## Start up

Web server and browser page are started
up by means of a script called `tf` or `text-fabric`, which will be installed in an executable
directory by the `pip` installer.

## Routes

There are 4 kinds of routes in the web app:

url pattern | effect
--- | ---
`/browser/static/...` | serves a static file from the server-wide [static folder](https://github.com/annotation/text-fabric/tree/master/tf/browser/static)
`/data/static/...` | serves a static file from the app specific static folder
`/local/static/...` | serves a static file from a local directory specified by the app
anything else | submits the form with user data and return the processed request

## Templates

There are two templates in
[views](https://github.com/annotation/text-fabric/tree/master/tf/browser/views)
:

* *index*: the normal template for returning responses
  to user requests;
* *export*: the template used for exporting results; it
  has printer/PDF-friendly formatting: good page breaks.
  Pretty displays always occur on a page by their own.
  It has very few user interaction controls.
  When saved as PDF from the browser, it is a neat record
  of work done, with DOI links to the corpus and to Text-Fabric.

## CSS

We format the web pages with CSS, with extensive use of
[flexbox](https://css-tricks.com/snippets/css/a-guide-to-flexbox).

There are several sources of CSS formatting:

* the CSS loaded from the app dependent extraApi, used
  for pretty displays;
* [index.css](https://github.com/annotation/text-fabric/blob/master/tf/browser/static/index.css):
  the formatting of the *index* web page with which the user interacts;
* [export.css](https://github.com/annotation/text-fabric/blob/master/tf/browser/views/export.css)
  the formatting of the export page;
* [base.css](https://github.com/annotation/text-fabric/blob/master/tf/browser/views/base.css)
  shared formatting between the index and export pages.

## Javascript

We use a
[modest amount of Javascript](https://github.com/annotation/text-fabric/blob/master/tf/browser/static/tf.js)
on top of
[JQuery](https://api.jquery.com).

For collapsing and expanding elements we use the
[details](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/details)
element. This is a convenient, Javascript-free way to manage
collapsing. Unfortunately it is not supported by the Microsoft
browsers, not even Edge.

!!! caution "On Windows?"
    Windows users should install Chrome of Firefox.
"""

import sys

from flask import Flask, send_file
from werkzeug.serving import run_simple

from ..parameters import HOST, GH
from ..core.helpers import console
from ..core.files import abspath, fileExists, dirNm
from ..core.timestamp import AUTO
from ..advanced.app import findApp

from .command import argApp
from .kernel import makeTfKernel
from .serve import (
    serveTable,
    serveQuery,
    servePassage,
    serveExport,
    serveDownload,
    serveAll,
)

# Here we import additional annotation tools
from .ner.web import factory as nerFactory
# End of importing additional annotation tools


TF_DONE = "TF setup done."
TF_ERROR = "Could not set up TF"

MY_DIR = dirNm(abspath(__file__))


class Web:
    def __init__(self, kernelApi):
        self.debug = False
        self.kernelApi = kernelApi
        app = kernelApi.app
        self.context = app.context
        self.wildQueries = set()

    def console(self, msg):
        if self.debug:
            console(msg)


def factory(web):
    app = Flask(__name__)

    # Here we add the annotation tools as blue prints
    app.register_blueprint(nerFactory(web))
    # End of adding annotation tools

    aContext = web.context
    appPath = aContext.appPath
    localDir = aContext.localDir

    @app.route("/browser/static/<path:filepath>")
    def serveStatic(filepath):
        theFile = f"{MY_DIR}/static/{filepath}"
        return send_file(theFile) if fileExists(theFile) else ""

    @app.route("/data/static/<path:filepath>")
    def serveData(filepath):
        theFile = f"{appPath}/static/{filepath}"
        return send_file(theFile) if appPath and fileExists(theFile) else ""

    @app.route("/local/<path:filepath>")
    def serveLocal(filepath):
        theFile = f"{localDir}/{filepath}"
        return send_file(theFile) if fileExists(theFile) else ""

    @app.route("/sections", methods=["GET", "POST"])
    def serveSectionsBare():
        return serveTable(web, "sections", None)

    @app.route("/sections/<int:getx>", methods=["GET", "POST"])
    def serveSections(getx):
        return serveTable(web, "sections", getx)

    @app.route("/tuples", methods=["GET", "POST"])
    def serveTuplesBare():
        return serveTable(web, "tuples", None)

    @app.route("/tuples/<int:getx>", methods=["GET", "POST"])
    def serveTuples(getx):
        return serveTable(web, "tuples", getx)

    @app.route("/query", methods=["GET", "POST"])
    def serveQueryBare():
        return serveQuery(web, None)

    @app.route("/query/<int:getx>", methods=["GET", "POST"])
    def serveQueryX(getx):
        return serveQuery(web, getx)

    @app.route("/passage", methods=["GET", "POST"])
    def servePassageBare():
        return servePassage(web, None)

    @app.route("/passage/<getx>", methods=["GET", "POST"])
    def servePassageX(getx):
        return servePassage(web, getx)

    @app.route("/export", methods=["GET", "POST"])
    def serveExportX():
        return serveExport(web)

    @app.route("/download", methods=["GET", "POST"])
    def serveDownloadX():
        return serveDownload(web, False)

    @app.route("/downloadj", methods=["GET", "POST"])
    def serveDownloadJ():
        return serveDownload(web, True)

    @app.route("/", methods=["GET", "POST"])
    @app.route("/<path:anything>", methods=["GET", "POST"])
    def serveAllX(anything=None):
        return serveAll(web, anything)

    return app


def main(cargs=sys.argv[1:]):
    args = []
    debug = False

    for arg in cargs:
        if arg == "debug":
            debug = True
        else:
            args.append(arg)

    if len(args) == 0:
        console("No port number specified")
        console(f"{TF_ERROR}")
        return

    (portWeb, args) = (args[0], args[1:])

    appSpecs = argApp(args, False)

    if not appSpecs:
        console("No TF dataset specified")
        return

    backend = appSpecs.get("backend", GH) or GH
    appName = appSpecs["appName"]
    checkout = appSpecs["checkout"]
    checkoutApp = appSpecs["checkoutApp"]
    dataLoc = appSpecs["dataLoc"]
    moduleRefs = appSpecs["moduleRefs"]
    locations = appSpecs["locations"]
    modules = appSpecs["modules"]
    setFile = appSpecs["setFile"]
    version = appSpecs["version"]

    if checkout is None:
        checkout = ""

    versionRep = "" if version is None else f" version {version}"
    console(
        f"Setting up TF browser for {appName} {moduleRefs or ''} "
        f"{setFile or ''}{versionRep}"
    )
    app = findApp(
        appName,
        checkoutApp,
        dataLoc,
        backend,
        True,
        silent=AUTO,
        checkout=checkout,
        mod=moduleRefs,
        locations=locations,
        modules=modules,
        setFile=setFile,
        version=version,
    )
    if app is None:
        console(f"{TF_ERROR}")
        return

    try:
        web = Web(makeTfKernel(app, appName))
        console(f"{TF_DONE}")

        webapp = factory(web)
        if debug:
            webapp.config['TEMPLATES_AUTO_RELOAD'] = True
        web.debug = debug
        run_simple(
            HOST,
            int(portWeb),
            webapp,
            use_reloader=debug,
            use_debugger=False,
        )
    except OSError as e:
        console(str(e))
        console(f"{TF_ERROR}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())