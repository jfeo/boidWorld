import socketserver, socket, argparse, configparser, os, threading, queue, json,\
       math, time

# Server implementation
class AppUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    def __init__(self, server_address, RequestHandlerClass, app, bind_and_activate=True):
        self.app = app
        self.connections = {}
        self.counter = 0
        socketserver.UDPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)

class UDPRequestHandler(socketserver.DatagramRequestHandler):

    def setup(self):
        socketserver.DatagramRequestHandler.setup(self)

    def parse_message(self):
        pass

    def handle(self):
        msg = self.rfile.read()
        req = json.loads(str(msg, "utf-8"))
        if "type" in req:
            if req["type"] == "init":
                print("INIT request.")
                pcon = PlayerConnection()
                self.server.app.world.boids.append(pcon.boid)
                self.server.connections[(self.client_address[0], self.server.counter)] = pcon
                data = json.dumps({"type":"init", "id":self.server.counter, "status":"success"})
                self.server.counter += 1
                self.wfile.write(bytes(data, "utf-8"))
            elif "id" in req and (self.client_address[0], int(req["id"])) in self.server.connections:
                if req["type"] == "state":
                    pcon = self.server.connections[self.client_address]
                    if "state" in req:
                        print("STATE request.")
                        correction = self.server.app.world.checkstate(req["state"])
                        if correction == None:
                            data = json.dumps({"type":"state", "status":"accepted"})
                            self.wfile.write(bytes(data, "utf-8"))
                        else:
                            data = json.dumps({"type":"state", "status":"rejected",
                                               "state":self.pcon.get_state()})
                            self.wfile.write(bytes(data, "utf-8"))
                elif req["type"] == "world":
                    print("WORLD request.")
                    pcon = self.server.connections[(self.client_address[0], int(req["id"]))]
                    data = json.dumps({"type":"world", "boids":[boid for boid in self.server.app.world.boids
                               if boid != pcon.boid]})
                    self.wfile.write(bytes(data, "utf-8"))
                elif req["type"] == "deinit":
                    print("DEINIT request.")
                    self.server.app.world.boids.remove(self.server.connections[self.client_address].boid)
                    del self.server.connections[self.client_address]
                    self.wfile.write(bytes(json.dumps({"type":"deinit", "status":"success"}), "utf-8"))
            else:
                print(self.server.connections)
                self.wfile(bytes(json.dumps({"type":"error", "msg":"Not connected"}), "utf-8"))

class PlayerConnection(object):
    def __init__(self):
        self.seentime = int(time.time())
        self.boid = Boid()

# Game implementation
class Boid(object):
    def __init__(self):
        self.pos = (0.0, 0.0)
        self.moving = False
        self.ori = 0

    def get_state(self):
        pass

class World(object):
    def __init__(self):
        self.boids = []

# Server application
class Application(object):
    def __init__(self, port):
        self.serverThread = threading.Thread(target=self.serve, args=(port,))
        self.worldThread = threading.Thread(target=self.simulate)
        self.messages = queue.Queue()
        self.world = World()

    def start(self):
        print("Starting server thread.")
        self.serverThread.start()
        print("Starting world thread.")
        self.worldThread.start()

    def simulate(self):
        pass

    def serve(self, port):
        print(port)
        self.tcp = AppUDPServer(("localhost", port), UDPRequestHandler, self)
        self.tcp.serve_forever()

    def stop(self):
        self.tcp.shutdown()

# Application details
class ConfigAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if os.path.isfile(values):
            config = configparser.ConfigParser()
            try:
                config.read(values)
            except configparser.ParsingError:
                raise argparse.ArgumentTypeError("'%s' could not be parsed." % values)
            setattr(namespace, 'config', config)
        else:
            raise argparse.ArgumentTypeError("'%s' does not exist." % (values))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='SimpleMMO server.')
    parser.add_argument('-c', action=ConfigAction)
    args = parser.parse_args()

    app = Application(int(args.config['network'].get('port', 8555)))
    try:
        app.start()
    except KeyboardInterrupt:
        app.stop()
