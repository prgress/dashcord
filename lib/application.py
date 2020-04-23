import nest_asyncio

import asyncio
import inspect
import mimetypes
import urllib

from io import BytesIO

import socket
from socketserver import ThreadingMixIn
from http.server import SimpleHTTPRequestHandler, HTTPServer

PORT = 5000
HOST = socket.gethostname()

class DataTransfer:
    pass

data = DataTransfer()

class HTTPResponse:
    """Object to hold data about the response. No data is given if a GET request is passed."""
    
    def __init__(self, method, data=None):
        """
		Parameters:
			method {[string]} -- The request method. Either GET or POST

		Keyword Arguments:
			data {[dict]} -- The POST request's json data (default: {None})
		"""

        self.method = method
        
        self._original_data = data
        
        if data:
            self._json = data.get("json")
        
    
    async def json(self):
        """Get the response json"""
        return self._json
        
class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass

class HTTPRequestHandler(SimpleHTTPRequestHandler):
    """The handler that handles all of our website's requests, and calls the routing functions"""
    
    def do_GET(self):
        """This function handles the GET requests for the site."""
        
        if not data.bot:
            return self.wfile.write(b"Bot not supplied, wait a few seconds and refresh.")
        
        path = self.path.replace("/", "")
        
        if path == "":
            path = "index"
        
        if path.endswith(".js"):
            self.send_header("Content-type", "application/javascript")
            
            with open("%s/%s" % (data.static_path, path), "r") as f:
                return self.wfile.write(f.read().encode())
        if path.endswith(".css"):
            self.send_header("Content-type", "text/css")
            
            with open("%s/%s" % (data.static_path, path), "r") as f:
                return self.wfile.write(f.read().encode())
        
        if path in dir(data.routing_file):
            route_func = getattr(data.routing_file, path)
        else:
            return self.wfile.write(b"404, page not found")

        if not inspect.iscoroutinefunction(route_func):
            raise ValueError("Route function must be a coroutine.")
        
        try:
            result = data.loop.run_until_complete(route_func(data.bot, HTTPResponse("GET")))
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
            
            with open("%s/%s" % (data.static_path, path), "r") as f:
                return self.wfile.write(f.read().encode())
        if path.endswith(".css"):
            self.send_header("Content-type", "text/css")
            
            with open("%s/%s" % (data.static_path, path), "r") as f:
                return self.wfile.write(f.read().encode())
            
        body = self.rfile.read(int(self.headers.get("Content-Length"))).decode("utf-8").replace("+", " ")
        body = urllib.parse.unquote(body)
        
        json = {}
        for kv in body.split("&"):
            key = kv.split("=")[0]
            value = kv.split("=")[1]

            json[key] = value

        self.send_response(200)
        self.end_headers()
        
        response = HTTPResponse("POST", {"json": json})
        
        
        if path in dir(data.routing_file):
            route_func = getattr(data.routing_file, path)
        else:
            return self.wfile.write(b"404, page not found")

        self.send_response(200)

        if not inspect.iscoroutinefunction(route_func):
            raise ValueError("Route function must be a coroutine.")
        
        try:
            result = data.loop.run_until_complete(route_func(data.bot, response))
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

        self.bot = bot
        self.loop = bot.loop
        
        nest_asyncio.apply(self.loop)
        
        self.routing_file = routing_file
        data.routing_file = routing_file
        
        self.template_path = template_path
        data.template_path = template_path
        
        self.static_path = static_path
        data.static_path = static_path
        
        bot.dashboard = self
        
        data.bot = bot
        data.loop = self.loop
        
        self.server = ThreadingSimpleServer(("localhost", PORT), HTTPRequestHandler)
        
        self.bot.server = self.server
    
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
        with open(fp, "r") as html_file:
            contents = html_file.read()
            
            for token, body in dict(kwargs).items():
                contents = contents.replace("{{%s}}" % str(token), str(body))
        
            return contents
    
    async def start(self):
        """Start the web server"""
        
        print("Serving traffic from", HOST, "on port", PORT)
        self.server = self.bot.server

        while True:                
            self.bot.server.handle_request()