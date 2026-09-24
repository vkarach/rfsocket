import network
import socket
import time

import config
import display
import dy08

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


def switch(name, action):
    code = config.CHANNELS[name]["on" if action else "off"]
    dy08.send_raw(code[0], code[1])
    states[name] = action


def handle(path):
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

    switch(name, action)
    display.show(ip, states)
    return "on" if action else "off"


def serve():
    address = socket.getaddrinfo("0.0.0.0", HTTP_PORT)[0][-1]
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(address)
    server.listen(1)

    while True:
        client, _ = server.accept()
        try:
            request = client.recv(256).decode()
            path = request.split(" ")[1] if " " in request else ""
            body = handle(path)
            if body is None:
                client.send(RESPONSE_TEMPLATE.format(status="404 Not Found", body="unknown command"))
            else:
                client.send(RESPONSE_TEMPLATE.format(status="200 OK", body=body))
        except Exception as exc:
            print("request failed:", exc)
        finally:
            client.close()


ip = connect_wifi()
print("ip:", ip)
display.show(ip, states)
serve()
