import asyncio
import collections
import logging
import traceback

from proxycore.parser import http_parser
from proxycore.parser.http_parser import HttpMessage, HttpResponse
from proxycore.parser.parser_utils import intialize_parser, parse
from proxycore.pipe.logger import logger
from proxycore.pipe.reporting import MessageListener, LogReport

BUFFER_SIZE = 65536
CONNECT_TIMEOUT_SECONDS = 5

logger = logging.getLogger(__name__)


class EndpointParameters:
    def __init__(self, address, port):
        self.address = address
        self.port = port


class InputEndpointParameters(EndpointParameters):
    def __init__(self, address, port, listener):
        super().__init__(address, port)
        self.listener = listener


class Endpoint:
    def __init__(self, name: str, parameters: EndpointParameters):
        self.writer = None
        self.reader = None
        self.name = name
        self.parameters = parameters
        self.connection_string = "Not connected"

    async def _write_message(self, message: HttpMessage):
        for data in message.to_bytes():
            self.writer.write(data)
        await self.writer.drain()

    async def read_loop(self, async_callback):
        try:
            parser = intialize_parser(http_parser.get_http_request)
            while True:
                data = await self.reader.read(BUFFER_SIZE)

                for msg in parse(parser, data):
                    await async_callback(msg)

                if not data:
                    break
        except Exception as e:
            logger.info('proxy_task exception {}'.format(e))
            import traceback
            traceback.print_exc()
            raise

    async def close(self):
        if self.writer:
            self.writer.close()
            logger.info('close connection {}'.format(self.connection_string))

    async def on_received(self, message: HttpMessage):
        pass

    async def send(self, message: HttpMessage, processing):
        pass


class InputEndpoint(Endpoint):
    def __init__(self, name: str, parameters: InputEndpointParameters):
        super().__init__(name, parameters)
        self.parameters = parameters
        self.flow = None

    async def on_received(self, message: HttpMessage):
        flow = self.flow(message)
        processing = Processing(self.name, flow, listener=self.parameters.listener)
        processing.log_request(self.name, message)
        endpoint_name, message = processing.send_message(None)
        return processing, endpoint_name, message

    async def send(self, message: HttpMessage, processing):
        processing.log_response(self.name, message)
        await self._write_message(message)

    async def listen(self, handle_client):
        try:
            server = await asyncio.start_server(
                handle_client, host=self.parameters.address, port=self.parameters.port)
        except Exception as e:
            logger.error('Bind error: {}'.format(e))
            raise

        for s in server.sockets:
            logger.info('listening on {}'.format(s.getsockname()))

        return server

    async def connection_opened(self, reader, writer, flow):
        self.connection_string = '{} -> {}'.format(
            writer.get_extra_info('peername'),
            writer.get_extra_info('sockname'))
        self.writer = writer
        self.reader = reader
        self.flow = flow


class OutputEndpoint(Endpoint):
    def __init__(self, name: str, parameters: EndpointParameters):
        super().__init__(name, parameters)
        self.pending_processsings = collections.deque()

    async def send(self, message: HttpMessage, processing):
        self.pending_processsings.append(processing)
        processing.log_request(self.name, message)
        await self._write_message(message)

    async def on_received(self, message: HttpMessage):
        assert len(self.pending_processsings) > 0, "Response without a request"
        processing = self.pending_processsings.popleft()
        processing.log_response(self.name, message)
        endpoint_name, message = processing.send_message(message)
        return processing, endpoint_name, message

    async def open_connection(self):
        try:
            (remote_reader, remote_writer) = await asyncio.wait_for(
                asyncio.open_connection(host=self.parameters.address, port=self.parameters.port),
                timeout=CONNECT_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            logger.info('connect timeout')
            raise
        except Exception as e:
            logger.info('error connecting to remote server: {}'.format(e))
            raise
        else:
            self.connection_string = '{} -> {}'.format(
                remote_writer.get_extra_info('sockname'),
                remote_writer.get_extra_info('peername'))
            logger.info('connected to remote {}'.format(self.connection_string))
            self.reader = remote_reader
            self.writer = remote_writer


class ProcessingFinishedError(ValueError):
    pass


class Processing:
    def __init__(self, source_endpoint, flow, listener: MessageListener = None):
        self.source_endpoint = source_endpoint
        self.flow = flow
        self.log = LogReport()
        self.listener = listener

    def send_message(self, message):
        if self.has_finished():
            raise ProcessingFinishedError("Flow has already finished")

        try:
            return self.flow.send(message)
        except StopIteration as e:
            self.flow = None
            return self.source_endpoint, e.value
        except Exception as e:
            self.flow = None
            trace = traceback.format_exception(e.__class__, e, e.__traceback__)
            trace = "".join(trace)
            logger.error(trace)

            header = "Internal proxy error:\n"
            header += str(e) + "\n\n"

            response = HttpResponse(b"500", b"Internal proxy error",
                                    body=(header + trace).encode())

            return self.source_endpoint, response

    def has_finished(self):
        return self.flow is None

    def log_request(self, endpoint_name, message):
        self.log.log_request(endpoint_name, message)
        if self.listener:
            self.listener.on_change(self.log)

    def log_response(self, endpoint_name, message):
        self.log.log_response(endpoint_name, message)
        if self.listener:
            self.listener.on_change(self.log)
