import asyncio
import network
import time

import clips
import clock
import config
import display
import dy08
import idle
import player
import rf
import stream

HTTP_PORT = 80
CLIPS_ROOT = "/clips"
SCREEN_TICK_S = 1
NTP_INTERVAL_S = 6 * 3600
NTP_RETRY_S = 60

RESPONSE_TEMPLATE = (
    "HTTP/1.0 {status}\r\n"
    "Content-Type: text/plain\r\n"
    "Connection: close\r\n"
    "\r\n"
    "{body}"
)

states = {name: 0 for name in config.CHANNELS}
ip = ""
wall_clock = clock.Clock(time.ticks_diff)
idle_timer = idle.IdleTimer(config.CLOCK_AFTER_S * 1000, config.SLEEP_AFTER_S * 1000,
                            time.ticks_ms(), time.ticks_diff)
clip_store = clips.ClipStore(CLIPS_ROOT, config.CLIP_BUDGET, config.CLIP_MAX_COUNT, config.CLIP_AUTO_MAX)
player.init(clip_store)


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
    path, query = (path.split("?", 1) + [""])[:2]
    parts = [part for part in path.split("/") if part]

    if parts == ["state"]:
        return " ".join("%s:%s" % (name, "on" if states[name] else "off")
                        for name in sorted(states))

    if parts and parts[0] == "clips":
        return await handle_clips(parts[1:], query.split("&"))

    if len(parts) != 2:
        return None

    name, command = parts[0].lower(), parts[1].lower()
    if name == "screen":
        return pin_screen(command)
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


def list_clips():
    # Name goes last because it may contain spaces.
    return "\n".join("%s %d %d %s %s" % (entry["id"], entry["frames"], (entry["size"] + 1023) // 1024,
                                         "*" if entry["star"] else "-", entry["name"])
                     for entry in clip_store.list())


async def handle_clips(parts, flags):
    if not parts:
        return list_clips()
    if parts == ["stop"]:
        player.stop()
        return "stopped"
    if len(parts) != 2:
        return None

    clip_id, command = parts[0], parts[1].lower()
    if command == "play":
        once = "once" in flags
        if not player.play(clip_id, once):
            return None
        return "playing %s%s" % (clip_id, " once" if once else "")
    if command not in ("star", "unstar", "delete"):
        return None
    if command == "delete" and clip_store.playing == clip_id:
        player.stop()
    async with rf.lock:
        done = getattr(clip_store, command)(clip_id)
    return "%s %s" % (command, clip_id) if done else None


def pin_screen(command):
    if command == "auto":
        idle_timer.pin(None)
        body = "screen: auto (idle timers)"
    elif command in idle.SCREENS:
        idle_timer.pin(command)
        body = "screen pinned: %s" % command
    else:
        return None
    wake()
    return body


def wake():
    now = time.ticks_ms()
    idle_timer.touch(now)
    display.set_screen(idle_timer.screen(now))


async def screen_loop():
    while True:
        now = time.ticks_ms()
        if display.streaming():
            idle_timer.touch(now)
        unix = wall_clock.unix(now)
        display.set_time(None if unix is None else clock.local_hm(unix, config.TZ_OFFSET_S, config.TZ_EU_DST))
        display.set_screen(idle_timer.screen(now))
        await asyncio.sleep(SCREEN_TICK_S)


async def ntp_loop():
    while True:
        # DNS lookup inside fetch_unix blocks the loop, so never sync mid-stream.
        if display.streaming():
            await asyncio.sleep(NTP_RETRY_S)
            continue
        unix = await clock.fetch_unix(config.NTP_HOST)
        if unix is None:
            await asyncio.sleep(NTP_RETRY_S)
        else:
            wall_clock.set(unix, time.ticks_ms())
            await asyncio.sleep(NTP_INTERVAL_S)


async def serve_client(reader, writer):
    wake()
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
    await stream.serve(config.STREAM_PORT, clip_store)
    asyncio.create_task(ntp_loop())
    await screen_loop()


asyncio.run(main())
