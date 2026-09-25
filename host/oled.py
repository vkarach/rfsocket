import argparse
import itertools
import os
import sys

import clip
import convert
import protocol
import sender
import sources

DEFAULT_PORT = 7000
DEFAULT_DITHER = {"image": "fs", "gif": "bayer", "video": "bayer"}
# Matches the device CLIP_BUDGET; anything larger can never be stored, so stop recording early.
HISTORY_MAX_BYTES = 1024 * 1024
STORE_MESSAGES = {
    protocol.STORE_DONE: "saved %s",
    protocol.STORE_EXISTS: "already saved %s",
    protocol.STORE_TOO_LARGE: "not saved: too large for history",
    protocol.STORE_NO_SPACE: "not saved: no space (starred clips fill the budget)",
}


class Recorder:
    """Collects the first full pass of the stream for the device history."""

    def __init__(self, name):
        self.builder = clip.ClipBuilder(name)
        self.complete = False
        self.too_large = False

    def add(self, frame, duration):
        if not self.too_large:
            self.builder.add(frame, duration)
            self.too_large = self.builder.size > HISTORY_MAX_BYTES


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Stream an image, GIF or video to the rfsocket OLED.")
    parser.add_argument("file")
    parser.add_argument("--host", default=os.environ.get("RFSOCKET_HOST"),
                        help="device IP (default: $RFSOCKET_HOST)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    scale = parser.add_mutually_exclusive_group()
    scale.add_argument("--fit", dest="scale", action="store_const", const="fit")
    scale.add_argument("--fill", dest="scale", action="store_const", const="fill")
    parser.add_argument("--invert", action="store_true")
    parser.add_argument("--dither", choices=convert.DITHER_METHODS)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--keep", action="store_true", help="star the clip in the device history")
    parser.set_defaults(scale="fit")
    args = parser.parse_args(argv)
    if not args.host:
        parser.error("--host is required when RFSOCKET_HOST is not set")
    return args


def stream_frames(source, args, dither, recorder):
    passes = itertools.count() if args.loop and source.kind != "image" else range(1)
    for index in passes:
        for image, duration in source.frames():
            frame = convert.to_frame(image, args.scale, dither, args.invert)
            if index == 0:
                recorder.add(frame, duration)
            yield frame, duration
        if index == 0:
            recorder.complete = True


def save_to_history(args, recorder):
    if not recorder.complete:
        print("not saved: first pass incomplete")
        return 0
    if recorder.too_large:
        print("not saved: larger than %d KB" % (HISTORY_MAX_BYTES // 1024))
        return 0
    built = recorder.builder.finish()
    try:
        status = sender.store(args.host, args.port, built, args.keep)
    except sender.SenderError as exc:
        print("error: upload failed: %s" % exc, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("upload aborted")
        return 0
    if status not in STORE_MESSAGES:
        print("error: upload failed: device status %d" % status, file=sys.stderr)
        return 1
    message = STORE_MESSAGES[status]
    print(message % built.id if "%s" in message else message)
    return 0


def main(argv):
    args = parse_args(argv)
    stats = sender.PlayStats()
    recorder = Recorder(args.file)
    try:
        source = sources.open_source(args.file)
        dither = args.dither or DEFAULT_DITHER[source.kind]
        frames = stream_frames(source, args, dither, recorder)
        sock = sender.connect(args.host, args.port)
        try:
            sender.play(sock, frames, stats=stats)
            # The device drops back to the status screen on disconnect, so a still image keeps the link open.
            if source.kind == "image":
                sender.hold(sock)
        except KeyboardInterrupt:
            pass
        finally:
            sock.close()
    except (sources.SourceError, sender.SenderError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    print("sent %d, dropped %d" % (stats.sent, stats.dropped))
    return save_to_history(args, recorder)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
