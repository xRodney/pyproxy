#!/usr/bin/env python3

# Based on https://github.com/aaronriekenberg/asyncioproxy/blob/master/proxy.py

import asyncio
import logging
import sys
from threading import Thread

from parser import http_parser
from parser.parser_utils import intialize_parser, parse
from pipe.communication import MessageListener, MessagePairer, MessageProcessor

BUFFER_SIZE = 65536
CONNECT_TIMEOUT_SECONDS = 5


def create_logger():
    logger = logging.getLogger('proxy')
    logger.setLevel(logging.INFO)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s - %(threadName)s - %(message)s')
    consoleHandler.setFormatter(formatter)

    logger.addHandler(consoleHandler)

    return logger


logger = create_logger()


def client_connection_string(writer):
    return '{} -> {}'.format(
        writer.get_extra_info('peername'),
        writer.get_extra_info('sockname'))


def remote_connection_string(writer):
    return '{} -> {}'.format(
        writer.get_extra_info('sockname'),
        writer.get_extra_info('peername'))


async def proxy_data(reader, writer, connection_string, pairer, processor):
    try:
        parser = intialize_parser(http_parser.get_http_request)
        while True:
            data = await reader.read(BUFFER_SIZE)

            for msg in parse(parser, data):
                msg = processor.process_message(msg)
                pairer.add_message(msg)
                for data in msg.to_bytes():
                    writer.write(data)
                await writer.drain()

            if not data:
                break
    except Exception as e:
        logger.info('proxy_{}_task exception {}'.format(tag, e))
    finally:
        writer.close()
        logger.info('close connection {}'.format(connection_string))


async def accept_client(client_reader, client_writer, local_address, local_port, remote_address, remote_port, listener):
    client_string = client_connection_string(client_writer)
    logger.info('accept connection {}'.format(client_string))
    try:
        (remote_reader, remote_writer) = await asyncio.wait_for(
            asyncio.open_connection(host=remote_address, port=remote_port),
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

        pairer = MessagePairer(listener)
        processor = MessageProcessor(local_address, local_port, remote_address, remote_port)

        asyncio.ensure_future(proxy_data(client_reader, remote_writer, remote_string, pairer, processor))
        asyncio.ensure_future(proxy_data(remote_reader, client_writer, client_string, pairer, processor))


def parse_addr_port_string(addr_port_string):
    addr_port_list = addr_port_string.rsplit(':', 1)
    return (addr_port_list[0], int(addr_port_list[1]))


def print_usage_and_exit():
    logger.error(
        'Usage: {} <listen addr> <remote addr>'.format(
            sys.argv[0]))
    sys.exit(1)


def prepare_server(loop, local_address, local_port, remote_address, remote_port, listener=None):
    def handle_client(client_reader, client_writer):
        asyncio.ensure_future(accept_client(
            client_reader=client_reader, client_writer=client_writer,
            remote_address=remote_address, remote_port=remote_port,
            local_address=local_address, local_port=local_port,
            listener=listener
        ))

    try:
        server_future = asyncio.start_server(
            handle_client, host=local_address, port=local_port)
        server = loop.run_until_complete(server_future)
    except Exception as e:
        logger.error('Bind error: {}'.format(e))
        raise

    for s in server.sockets:
        logger.info('listening on {}'.format(s.getsockname()))

    return server


class PipeThread(Thread):
    def __init__(self, local_address, local_port, remote_address, remote_port, listener):
        Thread.__init__(self)
        self.listener = listener
        self.remote_port = remote_port
        self.remote_address = remote_address
        self.local_port = local_port
        self.local_address = local_address

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.server = prepare_server(self.loop,
                                     self.local_address, self.local_port,
                                     self.remote_address, self.remote_port,
                                     self.listener)

        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass

    def stop(self):
        self.server.close()
        self.loop.stop()


if __name__ == '__main__':
    try:
        if (len(sys.argv) != 3):
            raise Exception("arguments")
        (local_address, local_port) = parse_addr_port_string(sys.argv[1])
        (remote_address, remote_port) = parse_addr_port_string(sys.argv[2])
    except:
        print_usage_and_exit()
    else:
        loop = asyncio.get_event_loop()
        prepare_server(loop, local_address, local_port, remote_address, remote_port, MessageListener())
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
