import http.server as hs
import argparse
import socketserver
import socket # For gethostbyaddr()
import os
import sys
import configs

class HTTPServer(socketserver.TCPServer):
    
    allow_reuse_address = 1    # Seems to make sense in testing environment

    def server_bind(self):
        """Override server_bind to store the server name."""
        socketserver.TCPServer.server_bind(self)
        host = configs.http_server_host
        port = self.server_address[1]
        self.server_name = socket.getfqdn(host)
        self.server_port = port

def test(HandlerClass=hs.BaseHTTPRequestHandler,
         ServerClass=HTTPServer, protocol="HTTP/1.0", port=8000, bind=""):
    """Test the HTTP request handler class.

    This runs an HTTP server on port 8000 (or the port argument).

    """
    server_address = (bind, port)

    HandlerClass.protocol_version = protocol
    with ServerClass(server_address, HandlerClass) as httpd:
        sa = httpd.socket.getsockname()
        serve_message = "Serving HTTP on {host} port {port} (http://{host}:{port}/) ..."
        print(serve_message.format(host=sa[0], port=sa[1]))
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received, exiting.")
            sys.exit(0)

def run_httpserver():
    os.chdir("/edgefarm_config/Recording")

    parser = argparse.ArgumentParser()
    parser.add_argument('--cgi', action='store_true',
                        help='Run as CGI Server')
    parser.add_argument('--bind', '-b', default='', metavar='ADDRESS',
                        help='Specify alternate bind address '
                                '[default: all interfaces]')
    parser.add_argument('port', action='store',
                        default=configs.http_server_port, type=int,
                        nargs='?',
                        help='Specify alternate port [default: 8000]')
    args = parser.parse_args()
    if args.cgi:
        handler_class = hs.CGIHTTPRequestHandler
    else:
        handler_class = hs.SimpleHTTPRequestHandler
        
    test(HandlerClass=handler_class, port=args.port, bind=args.bind)