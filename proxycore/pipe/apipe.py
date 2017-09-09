#!/usr/bin/env python3

# Based on https://github.com/aaronriekenberg/asyncioproxy/blob/master/proxy.py

import asyncio
import sys
import threading
from threading import Thread

from typing import Iterable

import proxycore.flows
from proxycore.pipe.communication import FlowDefinition, Server
from proxycore.pipe.endpoint import InputEndpoint, OutputEndpoint, Endpoint, InputEndpointParameters, EndpointParameters
from proxycore.pipe.logger import logger
from proxycore.pipe.recipe.flow import Flow
from proxycore.pipe.recipe.flow_finder import register_flows
from proxycore.pipe.reporting import MessageListener

BUFFER_SIZE = 65536
CONNECT_TIMEOUT_SECONDS = 5


class ProxyParameters():
    def __init__(self, local_address, local_port, remote_address, remote_port):
        self.local_address = local_address
        self.local_port = local_port
        self.remote_address = remote_address
        self.remote_port = remote_port


def parse_addr_port_string(addr_port_string):
    addr_port_list = addr_port_string.rsplit(':', 1)
    return (addr_port_list[0], int(addr_port_list[1]))


def print_usage_and_exit():
    logger.error(
        'Usage: {} <listen addr> <remote addr>'.format(
            sys.argv[0]))
    sys.exit(1)


class PipeThread(Thread):
    def __init__(self, listener):
        Thread.__init__(self, daemon=True)
        self.listener = listener
        self.server = None
        self.__is_running = False
        self.loop = asyncio.new_event_loop()

    def run(self):
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass

    def start_proxy(self, proxy_parameters):
        future = asyncio.run_coroutine_threadsafe(
            self.__start_proxy(proxy_parameters),
            self.loop)
        ex = future.exception()
        if ex:
            raise ex
        else:
            self.__is_running = True

    async def __start_proxy(self, proxy_parameters):
        assert threading.current_thread() is self

        definition = ProxyFlowDefinition(proxy_parameters, proxycore.flows, self.listener)
        self.server = Server(definition)
        await self.server.start()

        assert self.server is not None

    def stop_proxy(self):
        asyncio.run_coroutine_threadsafe(self.__stop_proxy(), self.loop)
        self.__is_running = False

    async def __stop_proxy(self):
        assert threading.current_thread() is self
        if self.server:
            await self.server.close(wait_closed=True)
        self.server = None

    def is_running(self):
        return self.__is_running


class ProxyFlowDefinition(FlowDefinition):
    def __init__(self, parameters: ProxyParameters, module, listener: MessageListener):
        self.parameters = parameters
        self.module = module
        self.listener = listener
        self.__flow = None

    def get_flow(self, endpoint_name):
        if self.__flow is None:
            self.__flow = Flow(self.parameters)
            self.__flow = register_flows(self.module, self.__flow)
        return self.__flow

    def endpoints(self) -> Iterable[Endpoint]:
        yield InputEndpoint("local", InputEndpointParameters(
            self.parameters.local_address, self.parameters.local_port, self.listener))
        yield OutputEndpoint("remote", EndpointParameters(
            self.parameters.remote_address, self.parameters.remote_port))

    def reset(self):
        self.__flow = None


def main():
    try:
        if (len(sys.argv) != 3):
            raise Exception("arguments")
        (local_address, local_port) = parse_addr_port_string(sys.argv[1])
        (remote_address, remote_port) = parse_addr_port_string(sys.argv[2])
        proxy_parameters = ProxyParameters(local_address, local_port, remote_address, remote_port)
    except:
        print_usage_and_exit()
    else:
        loop = asyncio.get_event_loop()
        definition = ProxyFlowDefinition(proxy_parameters, proxycore.flows, MessageListener())
        server = Server(definition)
        loop.run_until_complete(server.start())
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
