import sys

import asyncio
from threading import Thread

import proxycore.flows
from proxycore.pipe.apipe import parse_addr_port_string
from proxycore.pipe.communication import FlowDefinition, Server
from proxycore.pipe.endpoint import InputEndpoint, InputEndpointParameters
from proxycore.pipe.logger import logger
from proxycore.pipe.recipe.flow import Flow
from proxycore.pipe.recipe.flow_finder import register_flows


class ServerParameters:
    def __init__(self, address, port):
        self.port = port
        self.address = address


class ServerFlowDefinition(FlowDefinition):
    def __init__(self, server_parameters, flow):
        self.flow = flow
        self.port = server_parameters.port
        self.address = server_parameters.address

    def get_flow(self, endpoint_name):
        return self.flow

    def endpoints(self):
        yield InputEndpoint("local", InputEndpointParameters(self.address, self.port, None))

    def print(self):
        print("Server on {}:{}".format(self.address, self.port))


class ServerThread(Thread):
    def __init__(self, server):
        Thread.__init__(self)
        self.server = server
        self.event_loop = None
        self.__is_running = False

    def run(self):
        print(self.server.print())
        self.__is_running = True

        self.event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.event_loop)
        self.event_loop.run_until_complete(self.server.start())
        try:
            self.event_loop.run_until_complete(self.server.wait_closed())
        except KeyboardInterrupt:
            pass

    def stop(self):
        self.__is_running = False
        self.server.kill()
        if self.event_loop:
            self.event_loop.stop()
        self.join()


def print_usage_and_exit():
    logger.error(
        'Usage: {} <listen addr> <timeout>'.format(
            sys.argv[0]))
    sys.exit(1)


def main():
    try:
        if (len(sys.argv) != 3):
            raise Exception("arguments")
        (local_address, local_port) = parse_addr_port_string(sys.argv[1])
        timeout = int(sys.argv[2])
        server_parameters = ServerParameters(local_address, local_port)
    except:
        print_usage_and_exit()
    else:
        loop = asyncio.get_event_loop()
        flow = register_flows(proxycore.flows, Flow(server_parameters))
        definition = ServerFlowDefinition(server_parameters, flow)
        server = Server(definition)
        loop.run_until_complete(server.start())
        try:
            if timeout > 0:
                loop.run_until_complete(asyncio.sleep(timeout))
            else:
                loop.run_forever()
        except KeyboardInterrupt:
            pass

        loop.stop()


if __name__ == '__main__':
    main()
