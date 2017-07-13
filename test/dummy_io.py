from proxy.pipe.endpoint import OutputEndpoint


class TestWriter:
    """
    Dummy for asyncio Writer.
    """

    def __init__(self):
        self.data = b""

    def write(self, data):
        self.data += data

    async def drain(self):
        pass

    def close(self):
        pass

    def get_extra_info(self, param):
        return "<extra_info:{}>".format(param)


class TestReader:
    """
    Dummy for asyncio Reader.
    """

    def __init__(self, data):
        self.data = data
        self.pos = 0

    async def read(self, len):
        pos1 = self.pos
        self.pos += len
        return self.data[pos1:self.pos]


class TestOutputEndpoint(OutputEndpoint):
    async def open_connection(self):
        self.writer = TestWriter()
