import network
import socket
import time

import config
import dy08
import display

HTTP_PORT = 80

RESPONSE_TEMPLATE = (
    "HTTP/1.0 {status}\r\n"
    "Content-Type: text/plain\r\n"
    "Connection: close\r\n"
    "\r\n"
    "{body}"
)

state = 0
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


def handle(path):
    global state


    if path == "/on":
        state = 1
    elif path == "/off":
        state = 0
    elif path == "/toggle":
        state = 0 if state else 1
    elif path == "/state":
        return "on" if state else "off"
    elif path == "/pair":
        for _ in range(5):
            dy08.send(config.SOCKET_ADDRESS, state)
            display.show(ip, state)
            return "on" if state else "off"
        state = 1
        return "paired"
    else:
        return None

    dy08.send(config.SOCKET_ADDRESS, state)
    display.show(ip, state)
    return "on" if state else "off"


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
display.show(ip, state)
serve()
