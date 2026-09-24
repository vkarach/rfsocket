import asyncio

from rf import send_pulses

# Protocol timings in microseconds, taken from the solight-dy08 library
FIRST_SHORT_US = 400
FIRST_LONG_US = 1100
FIRST_HEADER_US = 2388
FIRST_REPEATS = 2

SECOND_SHORT_US = 570
SECOND_LONG_US = 1500
SECOND_HEADER_US = 7292
SECOND_REPEATS = 2

GAP_US = 59400

_lock = asyncio.Lock()


def _add_byte(pulses, byte, short_us, long_us):
    for i in range(8):
        if byte & (0x80 >> i):
            pulses.append(long_us)
            pulses.append(short_us)
        else:
            pulses.append(short_us)
            pulses.append(long_us)


def _add_block(pulses, data, repeats, header_us, short_us, long_us):
    for _ in range(repeats):
        pulses.append(short_us)
        pulses.append(header_us)
        for byte in data:
            _add_byte(pulses, byte, short_us, long_us)


def build_frame(address, action):
    address &= (1 << 37) - 1

    first = [0x90, 0x24, 0x20 | (address >> 32)]
    second = [(address >> 24) & 0xFF, (address >> 16) & 0xFF,
              (address >> 8) & 0xFF, address & 0xFF]

    if action:
        first = [first[0] ^ 0x0E, first[1] ^ 0x49, first[2] ^ 0x90]
        second = [second[0] ^ 0xC3, second[1] ^ 0x21,
                  second[2] ^ 0x62, second[3] ^ 0x40]

    pulses = []
    _add_block(pulses, first, FIRST_REPEATS, FIRST_HEADER_US,
               FIRST_SHORT_US, FIRST_LONG_US)
    _add_block(pulses, second, SECOND_REPEATS, SECOND_HEADER_US,
               SECOND_SHORT_US, SECOND_LONG_US)
    return pulses


async def _transmit(pulses):
    async with _lock:
        await send_pulses(pulses, repeat=1)
        await asyncio.sleep_ms(GAP_US // 1000)


async def send(address, action):
    await _transmit(build_frame(address, action))


async def send_raw(first_word, second_word):
    first = [(first_word >> 16) & 0xFF, (first_word >> 8) & 0xFF, first_word & 0xFF]
    second = [(second_word >> 24) & 0xFF, (second_word >> 16) & 0xFF,
              (second_word >> 8) & 0xFF, second_word & 0xFF]

    pulses = []
    _add_block(pulses, first, FIRST_REPEATS, FIRST_HEADER_US,
               FIRST_SHORT_US, FIRST_LONG_US)
    _add_block(pulses, second, SECOND_REPEATS, SECOND_HEADER_US,
               SECOND_SHORT_US, SECOND_LONG_US)

    await _transmit(pulses)
