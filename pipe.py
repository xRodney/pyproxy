"""
Code adapted from here: http://code.activestate.com/recipes/114642-pinhole/, licensed under Python Software Foundation License

usage 'pinhole port host [newport]'

Pinhole forwards the port to the host specified.
The optional newport parameter may be used to
redirect to a different port.

eg. pinhole 80 webserver
    Forward all incoming WWW sessions to webserver.

    pinhole 23 localhost 2323
    Forward all telnet sessions to port 2323 on localhost.
"""
import time
import traceback
from socket import *
from threading import Thread

import http_parser
from parser_utils import intialize_parser, parse
from request_response import Communication

LOGGING = 0


def log(s):
    if LOGGING:
        print('%s:%s' % (time.ctime(), s))
        sys.stdout.flush()


class PipeThread(Thread):
    pipes = []

    def __init__(self, pinhole, source, sink, tag, communication, newhost, newport):
        Thread.__init__(self)
        self.pinhole = pinhole
        self.communication = communication
        self.tag = tag
        self.source = source
        self.sink = sink
        self.stopped = False

        if newport != 80:
            self.host_header = b"%s:%s" % (str(newhost).encode(), str(newport).encode())
        else:
            self.host_header = b"%s" % (str(newhost).encode())

        log('Creating new pipe thread  %s ( %s -> %s )' % \
            (self, source.getpeername(), sink.getpeername()))
        PipeThread.pipes.append(self)
        log('%s pipes active' % len(PipeThread.pipes))

    def send(self, data):
        # print(data)
        self.sink.send(data)

    def send_request(self, msg):
        for data in msg.to_bytes():
            self.send(data)

    def run(self):
        parser = intialize_parser(http_parser.get_http_request)
        while not self.stopped:
            try:
                try:
                    data = self.source.recv(1024)
                except ConnectionResetError:
                    data = None

                if self.tag == "request":
                    for msg in parse(parser, data):
                        self.communication.add_message(msg, self.tag)
                        # print(msg)
                        if msg.headers.get(b"Host"):
                            msg.headers[b"Host"] = self.host_header
                        self.send_request(msg)
                else:
                    for msg in parse(parser, data):
                        self.communication.add_message(msg, self.tag)
                        # print(msg)
                        if msg.headers.get(b"Transfer-Encoding", "") == b"chunked":
                            del msg.headers[b"Transfer-Encoding"]
                            msg.headers[b"Content-Length"] = str(len(msg.body)).encode()
                        self.send_request(msg)

                if not data:
                    break
            except Exception as ex:
                traceback.print_exception(ex)
                break

        log('%s terminating' % self)
        PipeThread.pipes.remove(self)
        log('%s pipes active' % len(PipeThread.pipes))

        if not self.stopped:
            self.stop()

    def stop(self):
        self.stopped = True
        print ("Stopping " + self.tag)
        if self.source:
            self.source.close()
        if self.sink:
            self.sink.close()
        self.pinhole.pipe_stopped(self)


class Pinhole(Thread):
    def __init__(self, port, newhost, newport, communication_class=Communication, listener=None, on_error=None):
        Thread.__init__(self)
        log('Redirecting: localhost:%s -> %s:%s' % (port, newhost, newport))
        self.port = port
        self.newhost = newhost
        self.newport = newport
        self.communication_class = communication_class
        self.listener = listener
        self.on_error = on_error
        self.pipes = []
        self.stopped = False

    def run(self):
        try:
            self.sock = socket(AF_INET, SOCK_STREAM)
            self.sock.bind(('', self.port))
            self.sock.listen(5)

            while not self.stopped:
                newsock, address = self.sock.accept()
                log('Creating new session for %s %s' % address)
                fwd = socket(AF_INET, SOCK_STREAM)
                fwd.connect((self.newhost, self.newport))
                comm = self.communication_class(self.listener)
                thread1 = PipeThread(self, newsock, fwd, 'request', comm, self.newhost, self.newport)
                thread1.start()
                thread2 = PipeThread(self, fwd, newsock, 'response', comm, self.newhost, self.newport)
                thread2.start()
                self.pipes += [thread1, thread2]
        except Exception as e:
            if self.on_error:
                self.on_error(e)
            raise e
        finally:
            if not self.stopped:
                self.stop()


    def stop(self):
        self.sock.close()
        self.stopped = True
        for thread in self.pipes:
            thread.stop()

    def pipe_stopped(self, pipe):
        self.pipes.remove(pipe)



if __name__ == '__main__':
    print('Starting Pinhole')

    import sys

    # sys.stdout = open('pinhole.log', 'w')

    if len(sys.argv) > 1:
        port = newport = int(sys.argv[1])
        newhost = sys.argv[2]
        if len(sys.argv) == 4: newport = int(sys.argv[3])
        Pinhole(port, newhost, newport).start()
    else:
        Pinhole(8003, 'www.example.com', 80).start()
