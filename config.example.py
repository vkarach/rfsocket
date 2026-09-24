WIFI_SSID = "ssid"
WIFI_PASSWORD = "password"

STATIC_IP = "192.168.1.50"
SUBNET_MASK = "255.255.255.0"
GATEWAY = "192.168.1.1"
DNS = "192.168.1.1"

# (24-bit first word, 32-bit second word) per action, captured with sniff.learn()
CHANNELS = {
    "a": {"on": (0x000000, 0x00000000), "off": (0x000000, 0x00000000)},
}
