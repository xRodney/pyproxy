import sys

import asyncio
from threading import Thread

import time

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

    def run(self):
        self.server.print()
        self.event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.event_loop)
        self.event_loop.run_until_complete(self.server.start())
        try:
            self.event_loop.run_until_complete(self.server.wait_closed())
        except KeyboardInterrupt:
            pass

    def stop(self):
        asyncio.run_coroutine_threadsafe(self.server.kill(), self.event_loop)
        self.join()


def print_usage_and_exit():
    logger.error(
        'Usage: {} <listen addr> <timeout>'.format(
            sys.argv[0]))
    sys.exit(1)


def main():
    try:
        if (len(sys.argv) < 2):
            raise Exception("arguments")
        (local_address, local_port) = parse_addr_port_string(sys.argv[1])
        server_parameters = ServerParameters(local_address, local_port)
    except:
        print_usage_and_exit()
    else:
        flow = register_flows(proxycore.flows, Flow(server_parameters))
        definition = ServerFlowDefinition(server_parameters, flow)
        server = Server(definition)
        thread = ServerThread(server)
        thread.start()
        try:
            while True:
                print("Server is running, CTRL+C to terminate")
                time.sleep(10)
        except KeyboardInterrupt:
            pass

        print("Terminating")
        thread.stop()
        print("Terminated")


if __name__ == '__main__':
    main()
