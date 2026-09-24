import pytest

import protocol


def test_frame_message_prefixes_type_byte():
    message = protocol.frame_message(bytes(range(256)) * 4)

    assert len(message) == protocol.FRAME_SIZE + 1
    assert message[0] == protocol.MSG_FRAME == 0x01
    assert message[1:] == bytes(range(256)) * 4


def test_frame_message_rejects_wrong_length():
    with pytest.raises(ValueError):
        protocol.frame_message(bytes(1023))
