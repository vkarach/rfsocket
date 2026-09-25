import json
import os

# Mirrors host/protocol.py STORE_* status bytes.
STORE_ACCEPT = 0
STORE_EXISTS = 1
STORE_TOO_LARGE = 2
STORE_NO_SPACE = 3
STORE_DONE = 4
STORE_FAILED = 5

INDEX = "index.json"
CLIP_EXT = ".clp"
TEMP_EXT = ".tmp"

# littlefs rename replaces the target; CPython on Windows needs os.replace for that.
_replace = getattr(os, "replace", os.rename)


def _exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def _remove(path):
    try:
        os.remove(path)
    except OSError:
        pass


class ClipWriter:
    def __init__(self, store, clip_id, name, frames, size, keep):
        self._store = store
        self._entry = {"id": clip_id, "name": name, "frames": frames, "size": size, "star": keep}
        self._temp = store._file(clip_id + TEMP_EXT)
        self._file = open(self._temp, "wb")
        self._written = 0

    def write(self, chunk):
        self._file.write(chunk)
        self._written += len(chunk)

    def abort(self):
        self._file.close()
        _remove(self._temp)

    def commit(self):
        self._file.close()
        if self._written != self._entry["size"]:
            _remove(self._temp)
            return STORE_FAILED
        return self._store._commit(self._entry, self._temp)


class ClipStore:
    def __init__(self, root, budget, max_count, auto_max):
        self.root = root
        self.budget = budget
        self.max_count = max_count
        self.auto_max = auto_max
        self.playing = None
        try:
            os.mkdir(root)
        except OSError:
            pass
        self._clips = self._load()
        self._recover()

    def _file(self, name):
        return self.root + "/" + name

    def path(self, clip_id):
        return self._file(clip_id + CLIP_EXT)

    def _load(self):
        try:
            with open(self._file(INDEX)) as f:
                return json.load(f)["clips"]
        except (OSError, ValueError, KeyError):
            return []

    def _save(self):
        temp = self._file(INDEX + TEMP_EXT)
        with open(temp, "w") as f:
            json.dump({"clips": self._clips}, f)
        _replace(temp, self._file(INDEX))

    def _recover(self):
        self._clips = [entry for entry in self._clips if _exists(self.path(entry["id"]))]
        known = set(entry["id"] + CLIP_EXT for entry in self._clips)
        for name in os.listdir(self.root):
            if name.endswith(TEMP_EXT) or (name.endswith(CLIP_EXT) and name not in known):
                _remove(self._file(name))
        self._save()

    def _find(self, clip_id):
        for index, entry in enumerate(self._clips):
            if entry["id"] == clip_id:
                return index
        return -1

    def list(self):
        return [dict(entry) for entry in reversed(self._clips)]

    def get(self, clip_id):
        index = self._find(clip_id)
        return dict(self._clips[index]) if index >= 0 else None

    def _evictions(self, size):
        """Ids to drop, oldest first, so `size` more bytes fit; None if starred/playing clips block it."""
        used = sum(entry["size"] for entry in self._clips)
        count = len(self._clips)
        victims = []
        for entry in self._clips:
            if used + size <= self.budget and count + 1 <= self.max_count:
                break
            if entry["star"] or entry["id"] == self.playing:
                continue
            victims.append(entry["id"])
            used -= entry["size"]
            count -= 1
        if used + size > self.budget or count + 1 > self.max_count:
            return None
        return victims

    def check(self, clip_id, size, keep):
        index = self._find(clip_id)
        if index >= 0:
            entry = self._clips.pop(index)
            entry["star"] = entry["star"] or keep
            self._clips.append(entry)
            self._save()
            return STORE_EXISTS
        if size > (self.budget if keep else self.auto_max):
            return STORE_TOO_LARGE
        if self._evictions(size) is None:
            return STORE_NO_SPACE
        return STORE_ACCEPT

    def open_writer(self, clip_id, name, frames, size, keep):
        return ClipWriter(self, clip_id, name, frames, size, keep)

    def _commit(self, entry, temp):
        victims = self._evictions(entry["size"])
        if victims is None:
            _remove(temp)
            return STORE_NO_SPACE
        _replace(temp, self.path(entry["id"]))
        self._clips = [e for e in self._clips if e["id"] not in victims]
        self._clips.append(entry)
        self._save()
        for clip_id in victims:
            _remove(self.path(clip_id))
        return STORE_DONE

    def _set_star(self, clip_id, star):
        index = self._find(clip_id)
        if index < 0:
            return False
        self._clips[index]["star"] = star
        self._save()
        return True

    def star(self, clip_id):
        return self._set_star(clip_id, True)

    def unstar(self, clip_id):
        return self._set_star(clip_id, False)

    def delete(self, clip_id):
        index = self._find(clip_id)
        if index < 0:
            return False
        self._clips.pop(index)
        self._save()
        _remove(self.path(clip_id))
        return True
