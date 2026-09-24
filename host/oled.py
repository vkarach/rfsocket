import argparse
import itertools
import os
import socket
import sys

import convert
import sender
import sources

DEFAULT_PORT = 7000
DEFAULT_DITHER = {"image": "fs", "gif": "bayer", "video": "bayer"}


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
    parser.set_defaults(scale="fit")
    args = parser.parse_args(argv)
    if not args.host:
        parser.error("--host is required when RFSOCKET_HOST is not set")
    return args


def main(argv):
    args = parse_args(argv)
    try:
        source = sources.open_source(args.file)
        dither = args.dither or DEFAULT_DITHER[source.kind]
        passes = itertools.repeat(None) if args.loop and source.kind != "image" else [None]
        frames = ((convert.to_frame(image, args.scale, dither, args.invert), duration)
                  for _ in passes for image, duration in source.frames())
        sock = sender.connect(args.host, args.port)
        try:
            stats = sender.play(sock, frames)
            sock.shutdown(socket.SHUT_WR)
        finally:
            sock.close()
    except (sources.SourceError, sender.SenderError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    print("sent %d, dropped %d" % (stats.sent, stats.dropped))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
