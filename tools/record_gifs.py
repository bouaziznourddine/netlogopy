"""Record the animated GIFs of the documentation from the example scripts.

    python tools/record_gifs.py              # every GIF
    python tools/record_gifs.py job-shop     # only the ones whose name contains "job-shop"

Each example calls ``time.sleep()`` once per animation step.  The script runs
the example as it is, replaces ``time.sleep`` with a recorder that saves the
NetLogo view (or the whole interface, for the widget example) at each step,
and assembles the images into ``docs/assets/gifs/<name>.gif`` with Pillow.
Needs NetLogo, JPype and Pillow.
"""

import os
import runpy
import sys
import tempfile
import time
import weakref

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "docs", "assets", "gifs")
EXAMPLES = os.path.join(ROOT, "Examples")

# name, script, what to capture, keep one step out of `every`, GIF width
RECORDINGS = [
    ("quickstart", "advanced/28-quickstart.py", "view", 1, 420),
    ("patches-diffuse", "advanced/29-patches-grid.py", "view", 1, 360),
    ("network-layout", "advanced/30-network-layout.py", "view", 1, 420),
    ("job-shop", "advanced/35-job-shop.py", "view", 5, 520),
    ("fire-with-python-agents", "complexe/Fire/Fire.py", "view", 2, 460),
    ("wolf-sheep-with-python-agents", "complexe/Wolf Sheep/Wolf.py", "view", 3, 380),
    ("add-widgets", "advanced/36-add-widgets.py", "interface", 4, 760),
    ("start-pause-stop", "advanced/37-start-pause-stop.py", "view", 2, 340),
    ("python-policy", "advanced/38-python-policy.py", "view", 6, 320),
    ("movement", "simple/2-movement.py", "view", 3, 360),
    ("appearance", "simple/3-appearance.py", "view", 2, 360),
]
FRAME_MS = 80          # time per frame in the GIF
HOLD_MS = 1500         # last frame, and the final pause of each example
MAX_FRAMES = 160


class Recorder:
    def __init__(self, capture, every, folder):
        self.capture, self.every, self.folder = capture, every, folder
        self.sessions = []
        self.frames = []
        self.steps = 0

    def session(self):
        alive = [ref() for ref in self.sessions]
        alive = [nl for nl in alive if nl is not None and not nl.closed]
        return alive[-1] if alive else None

    def snap(self, hold=False):
        nl = self.session()
        if nl is None or len(self.frames) >= MAX_FRAMES:
            return
        path = os.path.join(self.folder, f"{len(self.frames):04d}.png")
        try:
            if self.capture == "interface":
                nl.export_interface(path)
            else:
                nl.export_view(path)
        except Exception:                   # a world that is being rebuilt: skip the frame
            return
        self.frames.append((path, HOLD_MS if hold else FRAME_MS))

    def sleep(self, seconds):
        if seconds >= 1:                    # the pause at the end of an example
            self.snap(hold=True)
            return
        self.steps += 1
        if self.steps % self.every == 0:
            self.snap()


def record(name, script, capture, every, width):
    from netlogopy import core
    folder = tempfile.mkdtemp(prefix=f"netlogopy-{name}-")
    recorder = Recorder(capture, every, folder)
    original_init, original_sleep, original_close = core.NetLogo.__init__, time.sleep, core.NetLogo.close

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        recorder.sessions.append(weakref.ref(self))

    def close(self):
        if recorder.session() is self and recorder.steps:
            recorder.snap(hold=True)        # the final state, held (not helper sessions)
        original_close(self)

    if capture == "view":
        os.environ["NETLOGOPY_HEADLESS"] = "1"
    else:
        os.environ.pop("NETLOGOPY_HEADLESS", None)
    core.NetLogo.__init__, core.NetLogo.close, time.sleep = init, close, recorder.sleep
    cwd = os.getcwd()
    try:
        os.chdir(folder)
        runpy.run_path(os.path.join(EXAMPLES, script), run_name="__main__")
    finally:
        os.chdir(cwd)
        core.NetLogo.__init__, core.NetLogo.close, time.sleep = original_init, original_close, original_sleep
    return assemble(name, recorder.frames, width)


def assemble(name, frames, width):
    from PIL import Image
    if not frames:
        raise RuntimeError(f"{name}: no frame recorded")
    images, durations = [], []
    last = Image.open(frames[-1][0])
    size = (width, round(last.height * width / last.width))     # every frame at the final size
    for path, duration in frames:
        images.append(Image.open(path).convert("RGB").resize(size, Image.LANCZOS))
        durations.append(duration)
    durations[-1] = HOLD_MS
    palette = images[-1].quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    frames_p = [image.quantize(palette=palette, dither=Image.Dither.NONE) for image in images]
    os.makedirs(OUT, exist_ok=True)
    target = os.path.join(OUT, f"{name}.gif")
    frames_p[0].save(target, save_all=True, append_images=frames_p[1:], duration=durations,
                     loop=0, optimize=True, disposal=1)
    return target, len(frames_p), os.path.getsize(target)


if __name__ == "__main__":
    wanted = sys.argv[1:]
    for name, script, capture, every, width in RECORDINGS:
        if wanted and not any(word in name for word in wanted):
            continue
        started = time.monotonic()
        target, count, size = record(name, script, capture, every, width)
        print(f"{os.path.relpath(target, ROOT)}: {count} frames, {size / 1e6:.2f} MB, "
              f"{time.monotonic() - started:.0f} s", flush=True)
