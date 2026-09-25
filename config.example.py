WIFI_SSID = "ssid"
WIFI_PASSWORD = "password"

STATIC_IP = "192.168.1.50"
SUBNET_MASK = "255.255.255.0"
GATEWAY = "192.168.1.1"
DNS = "192.168.1.1"

STREAM_PORT = 7000

NTP_HOST = "pool.ntp.org"
TZ_OFFSET_S = 3600
TZ_EU_DST = True

CLOCK_AFTER_S = 60
SLEEP_AFTER_S = 300

CLIP_BUDGET = 1024 * 1024
CLIP_MAX_COUNT = 100
CLIP_AUTO_MAX = 256 * 1024

# (24-bit first word, 32-bit second word) per action, captured with sniff.learn()
CHANNELS = {
    "a": {"on": (0x000000, 0x00000000), "off": (0x000000, 0x00000000)},
}
