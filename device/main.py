import asyncio
import network
import time

import config
import display
import dy08
import stream

HTTP_PORT = 80

RESPONSE_TEMPLATE = (
    "HTTP/1.0 {status}\r\n"
    "Content-Type: text/plain\r\n"
    "Connection: close\r\n"
    "\r\n"
    "{body}"
)

states = {name: 0 for name in config.CHANNELS}
ip = ""


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.ifconfig((config.STATIC_IP, config.SUBNET_MASK, config.GATEWAY, config.DNS))
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(0.5)
    return wlan.ifconfig()[0]


async def switch(name, action):
    code = config.CHANNELS[name]["on" if action else "off"]
    await dy08.send_raw(code[0], code[1])


async def handle(path):
    parts = [part for part in path.split("/") if part]

    if parts == ["state"]:
        return " ".join("%s:%s" % (name, "on" if states[name] else "off")
                        for name in sorted(states))

    if len(parts) != 2:
        return None

    name, command = parts[0].lower(), parts[1].lower()
    if name not in config.CHANNELS:
        return None

    if command == "on":
        action = 1
    elif command == "off":
        action = 0
    elif command == "toggle":
        action = 0 if states[name] else 1
    else:
        return None

    states[name] = action
    display.show(ip, states)
    await switch(name, action)
    return "on" if action else "off"


async def serve_client(reader, writer):
    try:
        request = (await reader.read(256)).decode()
        path = request.split(" ")[1] if " " in request else ""
        body = await handle(path)
        if body is None:
            response = RESPONSE_TEMPLATE.format(status="404 Not Found", body="unknown command")
        else:
            response = RESPONSE_TEMPLATE.format(status="200 OK", body=body)
        writer.write(response.encode())
        await writer.drain()
    except Exception as exc:
        print("request failed:", exc)
    finally:
        writer.close()
        await writer.wait_closed()


async def main():
    global ip
    ip = connect_wifi()
    print("ip:", ip)
    display.show(ip, states)
    await asyncio.start_server(serve_client, "0.0.0.0", HTTP_PORT)
    await stream.serve(config.STREAM_PORT)
    while True:
        await asyncio.sleep(3600)


asyncio.run(main())
