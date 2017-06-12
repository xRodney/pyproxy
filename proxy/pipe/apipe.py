#!/usr/bin/env python3

# Based on https://github.com/aaronriekenberg/asyncioproxy/blob/master/proxy.py

import asyncio
import sys
import threading
from threading import Thread

from proxy.pipe import default_recipe
from proxy.pipe.communication import InputEndpoint, OutputEndpoint, Dispatcher
from proxy.pipe.logger import logger
from proxy.pipe.recipe.transform import Proxy
from proxy.pipe.reporting import MessageListener

BUFFER_SIZE = 65536
CONNECT_TIMEOUT_SECONDS = 5


class ProxyParameters():
    def __init__(self, local_address, local_port, remote_address, remote_port):
        self.local_address = local_address
        self.local_port = local_port
        self.remote_address = remote_address
        self.remote_port = remote_port


def client_connection_string(writer):
    return '{} -> {}'.format(
        writer.get_extra_info('peername'),
        writer.get_extra_info('sockname'))


def remote_connection_string(writer):
    return '{} -> {}'.format(
        writer.get_extra_info('sockname'),
        writer.get_extra_info('peername'))


async def accept_client(client_reader, client_writer, proxy_parameters, listener):
    client_string = client_connection_string(client_writer)
    logger.info('accept connection {}'.format(client_string))
    try:
        (remote_reader, remote_writer) = await asyncio.wait_for(
            asyncio.open_connection(host=proxy_parameters.remote_address, port=proxy_parameters.remote_port),
            timeout=CONNECT_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        logger.info('connect timeout')
        logger.info('close connection {}'.format(client_string))
        client_writer.close()
    except Exception as e:
        logger.info('error connecting to remote server: {}'.format(e))
        logger.info('close connection {}'.format(client_string))
        client_writer.close()
    else:
        remote_string = remote_connection_string(remote_writer)
        logger.info('connected to remote {}'.format(remote_string))

        flow = Proxy(proxy_parameters)
        default_recipe.recipe(flow)

        dispatcher = Dispatcher()
        dispatcher.add_endpoint(InputEndpoint("local", client_reader, client_writer, client_string, flow, listener))
        dispatcher.add_endpoint(OutputEndpoint("remote", remote_reader, remote_writer, remote_string))

        await dispatcher.loop()


def parse_addr_port_string(addr_port_string):
    addr_port_list = addr_port_string.rsplit(':', 1)
    return (addr_port_list[0], int(addr_port_list[1]))


def print_usage_and_exit():
    logger.error(
        'Usage: {} <listen addr> <remote addr>'.format(
            sys.argv[0]))
    sys.exit(1)


async def prepare_server(proxy_parameters, listener=None):
    def handle_client(client_reader, client_writer):
        asyncio.ensure_future(accept_client(
            client_reader=client_reader, client_writer=client_writer,
            proxy_parameters=proxy_parameters,
            listener=listener
        ))

    try:
        server = await asyncio.start_server(
            handle_client, host=proxy_parameters.local_address, port=proxy_parameters.local_port)
    except Exception as e:
        logger.error('Bind error: {}'.format(e))
        raise

    for s in server.sockets:
        logger.info('listening on {}'.format(s.getsockname()))

    return server


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
        self.server = await prepare_server(proxy_parameters, self.listener)
        assert self.server is not None

    def stop_proxy(self):
        asyncio.run_coroutine_threadsafe(self.__stop_proxy(), self.loop)
        self.__is_running = False

    async def __stop_proxy(self):
        assert threading.current_thread() is self
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        self.server = None

    def is_running(self):
        return self.__is_running


if __name__ == '__main__':
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
        loop.run_until_complete(
            prepare_server(proxy_parameters, MessageListener()))
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
