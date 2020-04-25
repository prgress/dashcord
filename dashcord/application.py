import asyncio
import inspect
import mimetypes
import urllib
import re

import socket
from socketserver import ThreadingMixIn
from http.server import SimpleHTTPRequestHandler, HTTPServer
from jinja2 import Template

import nest_asyncio

class DataTransfer:
    def __init__(self):
        self.routes = {}
        self.dynamics = {}

    pass

REGEX = {
    "int": r"(\d*)",
    "str": r"(\D*)"
}
CONVERSIONS = {
    "str": str,
    "int": int
}

DATA = DataTransfer()

def route(route: str, dynamic: bool = False):
    """Add a route to the application
    
    Arguments:
        route {str} -- The path to the route.
        dynamic {bool} -- This should be set to True if the route is dynamic
    """
    
    def wrapper(func):
        nonlocal route
        arguments = None
        regex = None
        
        if dynamic:
            matches = re.findall(r"(<(int)?[:]?.+?(?=>))", route)
            arguments = {}
            
            route = route.replace("<", "").replace(">", "")
            
            regex = "^%s$" % route
            for match in matches:
                variable = match[0].replace("%s:" % match[1], "").replace("<", "")

                if match[1] != "":
                    arguments[variable] = match[1]
                    regex = regex.replace("%s:%s" % (match[1], variable), REGEX[match[1]])
                else:
                    arguments[variable] = "str"
                    regex = regex.replace(variable, REGEX["str"])
                
                DATA.dynamics[regex] = (func, route, True, arguments, regex)

        DATA.routes[route] = (func, route, dynamic, arguments, regex)

        return func

    return wrapper

class HTTPResponse:
    """Object to hold data about the response. No data is given if a GET request is passed."""

    def __init__(self, method, local_data=None):
        """
        Parameters:
                method {[string]} -- The request method. Either GET or POST

        Keyword Arguments:
                data {[dict]} -- The POST request's json data (default: {None})
        """

        self.method = method

        self._original_data = local_data

        if local_data:
            self._json = local_data.get("json")


    async def json(self):
        """Get the response json"""
        return self._json

class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass

class HTTPRequestHandler(SimpleHTTPRequestHandler):
    """The handler that handles all of our website's requests, and calls the routing functions"""
    
    def do_GET(self):
        """This function handles the GET requests for the site."""

        if not DATA.bot:
            return self.wfile.write(b"Bot not supplied, wait a few seconds and refresh.")

        path = self.path

        if path.endswith(".js"):
            self.send_header("Content-type", "application/javascript")

            with open("%s/%s" % (DATA.static_path, path.replace("/","")), "r") as file:
                return self.wfile.write(file.read().encode())
        if path.endswith(".css"):
            self.send_header("Content-type", "text/css")

            with open("%s/%s" % (DATA.static_path,  path.replace("/","")), "r") as file:
                return self.wfile.write(file.read().encode())

        dynamic = False
        match_object = None
        
        if path in DATA.routes.keys():
            route_data = DATA.routes.get(path)
            route_func = route_data[0]
        else:
            if not path.endswith(".ico") and len(path.split("/")) > 1:
                for r in DATA.dynamics.keys():
                    match = re.match(r, path)
                    if not match:
                        continue

                    match_object = match

                    if match.groups():
                        route_data = DATA.dynamics[r]
                        break
                else:
                    return self.wfile.write(b"404, page not found")

                route_func = route_data[0]
                dynamic = True
            else:
                return self.wfile.write(b"404, page not found")

        if not inspect.iscoroutinefunction(route_func):
            raise ValueError("Route function must be a coroutine.")

        try:
            kwargs = {}
            if dynamic:
                groups = match_object.groups()
                for i, kv in enumerate(route_data[3].items()):
                    try:
                        if kv[1] == "str":
                            if groups[i].isnumeric():
                                return self.wfile.write(b"404, page not found")
                        elif kv[1] == "int":
                            if not groups[i].isnumeric():
                                return self.wfile.write(b"404, page not found")
                            
                        kwargs[kv[0]] = CONVERSIONS[kv[1]](groups[i])
                    except ValueError:
                        return self.wfile.write(b"404, page not found")

                result = DATA.loop.run_until_complete(route_func(DATA.bot, HTTPResponse("GET"), **kwargs))
            else:
                result = DATA.loop.run_until_complete(route_func(DATA.bot, HTTPResponse("GET")))

        except RuntimeError as error:
            if str(error).startswith("Cannot enter into task"):
                pass

        if not isinstance(result, str):
            result = str(result)

        mimetype, _ = mimetypes.guess_type(path)
        self.send_response(200)
        self.send_header("Content-type", mimetype)
        self.end_headers()

        return self.wfile.write(result.encode())

    def do_POST(self):
        """This function handles the POST requests for the site."""

        path = self.path.replace("/", "")

        if path == "":
            path = "index"

        if path.endswith(".js"):
            self.send_header("Content-type", "application/javascript")

            with open("%s/%s" % (DATA.static_path, path), "r") as file:
                return self.wfile.write(file.read().encode())
        if path.endswith(".css"):
            self.send_header("Content-type", "text/css")

            with open("%s/%s" % (DATA.static_path, path), "r") as file:
                return self.wfile.write(file.read().encode())

        body = self.rfile.read(int(self.headers.get("Content-Length"))).decode("utf-8").replace("+", " ")
        body = urllib.parse.unquote(body)

        json = {}
        for key_value in body.split("&"):
            key = key_value.split("=")[0]
            value = key_value.split("=")[1]

            json[key] = value

        self.send_response(200)
        self.end_headers()

        response = HTTPResponse("POST", {"json": json})


        if path in dir(DATA.routing_file):
            route_func = getattr(DATA.routing_file, path)
        else:
            return self.wfile.write(b"404, page not found")

        self.send_response(200)

        if not inspect.iscoroutinefunction(route_func):
            raise ValueError("Route function must be a coroutine.")

        try:
            kwargs = {}
            if dynamic:
                groups = match_object.groups()
                for i, kv in enumerate(route_data[3].items()):
                    try:
                        if kv[1] == "str":
                            if groups[i].isnumeric():
                                return self.wfile.write(b"404, page not found")
                        elif kv[1] == "int":
                            if not groups[i].isnumeric():
                                return self.wfile.write(b"404, page not found")
                            
                        kwargs[kv[0]] = CONVERSIONS[kv[1]](groups[i])
                    except ValueError:
                        return self.wfile.write(b"404, page not found")

                result = DATA.loop.run_until_complete(route_func(DATA.bot, response, **kwargs))
            else:
                result = DATA.loop.run_until_complete(route_func(DATA.bot, response))

        except RuntimeError as error:
            if str(error).startswith("Cannot enter into task"):
                pass

        return self.wfile.write(str(result).encode())

class App:
    """The main dashcord application"""

    def __init__(self, bot, template_path, static_path, routing_file):
        """
        Parameters
        ----------
        bot
            The commands.Bot / discord.Client object.
        template_path
            The path for your html templates.
        static_path
            The path for your images, javascript and css files.
        routing_file
            The file holding your route functions.

            Usage is ```python
            import routing_file

            App(..., routing_file=routing_file)
            ```
        """

        DATA.app = self
        
        self.bot = bot
        self.loop = bot.loop

        nest_asyncio.apply(self.loop)

        self.routing_file = routing_file
        DATA.routing_file = routing_file

        self.template_path = template_path
        DATA.template_path = template_path

        self.static_path = static_path
        DATA.static_path = static_path

        bot.dashboard = self

        DATA.bot = bot
        DATA.loop = self.loop

    def render_html(self, fp, **kwargs):
        """
        Load a html file. Supports templating.

        Parameters
        ----------
        fp
            The html file, you don't need to supply the directory path.
        **kwargs
            Keyword arguments in this function are used to give the data to the html file for templating.
        """
        with open("%s/%s" % (self.template_path, fp), "r") as html_file:
            contents = html_file.read()

            template = Template(contents)
            return template.render(**kwargs)

    def begin_server(self, host, port):
        while True:
            self.bot.server.handle_request()

    async def start(self, host, port):
        """Start the web server"""
            
        print("Serving traffic from", host, "on port", port)

        self.server = ThreadingSimpleServer((host, port), HTTPRequestHandler)

        self.bot.server = self.server

        await self.loop.run_in_executor(None, self.begin_server, host, port)
