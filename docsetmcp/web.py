from starlette.requests import Request
from starlette.responses import RedirectResponse, Response, HTMLResponse
from starlette.staticfiles import StaticFiles
from tdom import Node, html  # cspell: disable-line

routes = []


def route(path: str):
    """Decorator to register a route handler for a specific path"""

    def decorator[T](func: T) -> T:
        routes.append((path, func))
        return func

    return decorator


@route("/docs/")
async def doc_listing(_request: Request) -> Response:
    import docsetmcp.server

    docsets = docsetmcp.server.extractors.values()
    # fmt: off
    body = html(t"""
        <h1>Available Documentation</h1>
        <ul>
            {[t'<li><a href="/docs/{docset.id}/">{docset.title}</a> {docset.description or ""}</li>' for docset in docsets]}
        </ul>
    """)
    # fmt: on
    page = html_doc(body, "Available Documentation")
    return HTMLResponse(str(page))


@route("/docs/{docset_id}/{path:path}")
async def doc_entry(request: Request) -> Response:
    import docsetmcp.server

    docset_id = request.path_params["docset_id"]
    extractor = docsetmcp.server.extractors.get(docset_id)
    if not extractor:
        return Response(status_code=404)

    path = request.path_params["path"]
    if path == "":
        return RedirectResponse(request.scope["path"] + extractor.starting_document)

    fileserver = StaticFiles(directory=extractor.documents_path, html=True)
    return await fileserver.get_response(path, request.scope)


def html_doc(body: Node, title: str) -> Node:
    return html(t"""
    <!doctype html>
    <html lang="en">
        <head>
            <title>{title}</title>
        </head>
        <body>{body}</body>
    </html>
    """)
