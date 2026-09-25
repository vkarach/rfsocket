import json
import os

import pytest

import clips

KB = 1024


def make_store(root, budget=100 * KB, max_count=100, auto_max=30 * KB):
    return clips.ClipStore(str(root), budget, max_count, auto_max)


def put(store, clip_id, size=10 * KB, keep=False, name=None):
    status = store.check(clip_id, size, keep)
    if status != clips.STORE_ACCEPT:
        return status
    writer = store.open_writer(clip_id, name or clip_id + ".gif", 3, size, keep)
    writer.write(b"x" * size)
    return writer.commit()


def ids(store):
    return [entry["id"] for entry in store.list()]


def test_store_and_list_newest_first(tmp_path):
    store = make_store(tmp_path)

    assert put(store, "aaa") == clips.STORE_DONE
    assert put(store, "bbb") == clips.STORE_DONE

    assert ids(store) == ["bbb", "aaa"]
    assert store.get("aaa") == {"id": "aaa", "name": "aaa.gif", "frames": 3, "size": 10 * KB, "star": False}
    assert os.path.getsize(store.path("aaa")) == 10 * KB


def test_auto_clip_above_auto_max_is_too_large(tmp_path):
    store = make_store(tmp_path)

    assert store.check("big", 31 * KB, False) == clips.STORE_TOO_LARGE


def test_keep_clip_may_use_whole_budget_and_is_starred(tmp_path):
    store = make_store(tmp_path)

    assert put(store, "big", size=100 * KB, keep=True) == clips.STORE_DONE
    assert store.get("big")["star"] is True
    assert store.check("huge", 101 * KB, True) == clips.STORE_TOO_LARGE


def test_eviction_removes_oldest_unstarred_first(tmp_path):
    store = make_store(tmp_path, budget=40 * KB)
    for clip_id in ["a", "b", "c", "d"]:
        put(store, clip_id)
    store.star("a")

    assert put(store, "e") == clips.STORE_DONE

    assert ids(store) == ["e", "d", "c", "a"]
    assert not os.path.exists(store.path("b"))


def test_eviction_skips_playing_clip(tmp_path):
    store = make_store(tmp_path, budget=30 * KB)
    for clip_id in ["a", "b", "c"]:
        put(store, clip_id)
    store.playing = "a"

    assert put(store, "d") == clips.STORE_DONE

    assert ids(store) == ["d", "c", "a"]


def test_count_limit_evicts(tmp_path):
    store = make_store(tmp_path, max_count=2)
    put(store, "a")
    put(store, "b")

    put(store, "c")

    assert ids(store) == ["c", "b"]


def test_no_space_when_only_starred_remain(tmp_path):
    store = make_store(tmp_path, budget=20 * KB)
    put(store, "a", keep=True)
    put(store, "b", keep=True)

    assert store.check("c", 10 * KB, False) == clips.STORE_NO_SPACE
    assert ids(store) == ["b", "a"]


def test_duplicate_is_exists_and_keep_stars_and_refreshes(tmp_path):
    store = make_store(tmp_path)
    put(store, "a")
    put(store, "b")

    assert store.check("a", 10 * KB, False) == clips.STORE_EXISTS
    assert store.get("a")["star"] is False
    assert store.check("a", 10 * KB, True) == clips.STORE_EXISTS
    assert store.get("a")["star"] is True
    assert ids(store) == ["a", "b"]


def test_abort_leaves_no_trace(tmp_path):
    store = make_store(tmp_path)
    put(store, "a")
    before = sorted(os.listdir(tmp_path))

    writer = store.open_writer("b", "b.gif", 3, 10 * KB, False)
    writer.write(b"x" * 100)
    writer.abort()

    assert sorted(os.listdir(tmp_path)) == before
    assert ids(store) == ["a"]


def test_short_payload_fails_commit(tmp_path):
    store = make_store(tmp_path)
    writer = store.open_writer("a", "a.gif", 3, 10 * KB, False)
    writer.write(b"x" * 100)

    assert writer.commit() == clips.STORE_FAILED
    assert ids(store) == []
    assert [name for name in os.listdir(tmp_path) if name != "index.json"] == []


def test_star_unstar_delete(tmp_path):
    store = make_store(tmp_path)
    put(store, "a")

    assert store.star("a") and store.get("a")["star"] is True
    assert store.unstar("a") and store.get("a")["star"] is False
    assert store.delete("a") is True
    assert store.get("a") is None
    assert not os.path.exists(store.path("a"))
    assert store.star("zzz") is False
    assert store.delete("zzz") is False


def test_index_survives_reload(tmp_path):
    store = make_store(tmp_path)
    put(store, "a", keep=True)
    put(store, "b")

    reloaded = make_store(tmp_path)

    assert reloaded.list() == store.list()


def test_recovery_cleans_orphans_temps_and_missing_files(tmp_path):
    store = make_store(tmp_path)
    put(store, "a")
    put(store, "b")
    os.remove(store.path("b"))
    (tmp_path / "orphan.clp").write_bytes(b"x")
    (tmp_path / "c.tmp").write_bytes(b"x")

    reloaded = make_store(tmp_path)

    assert ids(reloaded) == ["a"]
    assert sorted(os.listdir(tmp_path)) == ["a.clp", "index.json"]


def test_corrupt_index_starts_empty_and_removes_clips(tmp_path):
    store = make_store(tmp_path)
    put(store, "a")
    (tmp_path / "index.json").write_text("{not json")

    reloaded = make_store(tmp_path)

    assert reloaded.list() == []
    assert not os.path.exists(reloaded.path("a"))


def test_index_file_is_plain_json(tmp_path):
    store = make_store(tmp_path)
    put(store, "a")

    with open(tmp_path / "index.json") as f:
        assert json.load(f)["clips"][0]["id"] == "a"
