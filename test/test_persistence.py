import io
import os

import pytest

from pipe.persistence import parse_message_pairs, serialize_message_pairs

DIR = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture
def data():
    f = open(DIR + "/test_persistence.data", "rb")
    data = f.read()
    f.close()
    return data


def test_load_and_save(data):
    stream1 = io.BytesIO(data)
    message_pairs = list(parse_message_pairs(stream1))
    assert len(message_pairs) == 3

    # f = open(DIR + "/test_persistence.data2", "wb")
    # for pair in message_pairs:
    #     serialize_message_pair(pair, f)
    # f.close()

    stream2 = io.BytesIO()
    serialize_message_pairs(message_pairs, stream2)
    stream2.seek(0)
    data2 = stream2.read()
    assert data == data2
