import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import clip

OUT = os.path.join(os.path.dirname(__file__), "..", "android", "app", "src", "test",
                    "resources", "clip_fixtures")


def main():
    os.makedirs(OUT, exist_ok=True)
    builder = clip.ClipBuilder("sample clip.gif")
    for i in range(3):
        frame = bytes([(i * 37 + b) % 256 for b in range(1024)])
        builder.add(frame, duration_s=0.1 + i * 0.05)
    built = builder.finish()
    with open(os.path.join(OUT, "sample_clip.bin"), "wb") as f:
        f.write(built.data)
    with open(os.path.join(OUT, "sample_clip.id"), "w") as f:
        f.write(built.id)


if __name__ == "__main__":
    main()
