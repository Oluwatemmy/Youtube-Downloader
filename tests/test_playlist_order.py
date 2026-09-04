"""Playlist downloads keep the playlist's order on disk.

With 3 concurrent workers, item 7 can finish before item 2, and Explorer
sorts by name or date — neither is the playlist order. So playlist items
get a zero-padded position prefix: `03 - Title.mp4`."""
import pytest

from app import bridge


@pytest.mark.parametrize("item,expected", [
    ({"playlist_folder": "Course", "playlist_index": 3, "playlist_count": 12}, "03 - "),
    ({"playlist_folder": "Course", "playlist_index": 3, "playlist_count": 120}, "003 - "),
    ({"playlist_folder": "Course", "playlist_index": 12, "playlist_count": 12}, "12 - "),
    ({"playlist_folder": "Course", "playlist_index": 1, "playlist_count": 1}, "01 - "),
    ({"playlist_folder": "Course", "playlist_index": 7, "playlist_count": 0}, "07 - "),   # count unknown
    ({"playlist_folder": "Course", "playlist_index": 0, "playlist_count": 12}, ""),      # no position → no prefix
    ({"playlist_folder": "", "playlist_index": 3, "playlist_count": 12}, ""),            # not a playlist add
    ({}, ""),                                                                           # legacy queue rows
])
def test_playlist_prefix(item, expected):
    assert bridge._playlist_prefix(item) == expected


@pytest.fixture
def api(monkeypatch, tmp_path):
    monkeypatch.setattr(bridge, "SETTINGS_FILE", tmp_path / "settings.json")
    monkeypatch.setattr(bridge, "HISTORY_FILE", tmp_path / "history.json")
    monkeypatch.setattr(bridge, "QUEUE_FILE", tmp_path / "queue.json")
    monkeypatch.setattr(bridge, "LOGS_DIR", tmp_path / "logs")
    (tmp_path / "logs").mkdir()
    # Never hit the network: the worker task is a no-op in these tests.
    monkeypatch.setattr(bridge.DownloadManager, "_run", lambda self, id_, fresh=True: None)
    b = bridge.PyBridge()
    b._settings["folder"] = str(tmp_path / "dl")
    b._settings["dupes"] = False
    yield b
    b._mgr.shutdown()


def test_add_batch_records_playlist_positions(api):
    urls = ["https://youtu.be/b", "https://youtu.be/d"]      # user picked 2 of 4
    res = api.add_batch(urls, {
        "playlist_folder": "My Course",
        "playlist_indexes": {"https://youtu.be/b": 2, "https://youtu.be/d": 4},
        "playlist_count": 4,
    })

    items = {i["url"]: i for i in api._mgr.all()}
    assert len(res["ids"]) == 2
    assert items["https://youtu.be/b"]["playlist_index"] == 2
    assert items["https://youtu.be/b"]["playlist_count"] == 4
    assert items["https://youtu.be/d"]["playlist_index"] == 4
    assert bridge._playlist_prefix(items["https://youtu.be/d"]) == "04 - "


def test_add_batch_without_playlist_has_no_positions(api):
    api.add_batch(["https://youtu.be/x"], {})
    item = api._mgr.all()[0]
    assert item["playlist_index"] == 0
    assert bridge._playlist_prefix(item) == ""


def test_locate_finished_file_honours_prefix(api, tmp_path):
    folder = tmp_path / "dl" / "My Course"
    folder.mkdir(parents=True)
    (folder / "03 - Lecture Three.mp4").write_bytes(b"x")
    item = {"title": "Lecture Three", "playlist_folder": "My Course",
            "playlist_index": 3, "playlist_count": 10}

    found = api._mgr._locate_finished_file(item)

    assert found == str(folder / "03 - Lecture Three.mp4")


def test_locate_finished_file_still_works_without_prefix(api, tmp_path):
    folder = tmp_path / "dl"
    folder.mkdir(parents=True)
    (folder / "Solo Video.mp4").write_bytes(b"x")
    assert api._mgr._locate_finished_file({"title": "Solo Video"}) == str(folder / "Solo Video.mp4")


def test_remove_sweeps_prefixed_partials(api, tmp_path):
    folder = tmp_path / "dl" / "My Course"
    folder.mkdir(parents=True)
    part = folder / "03 - Lecture Three.f137.mp4.part"
    part.write_bytes(b"x")
    other = folder / "04 - Lecture Four.f137.mp4.part"
    other.write_bytes(b"x")
    ids = api.add_batch(["https://youtu.be/c"], {
        "playlist_folder": "My Course",
        "playlist_indexes": {"https://youtu.be/c": 3},
        "playlist_count": 10,
    })["ids"]
    api._mgr._update(ids[0], title="Lecture Three")

    api.remove(ids[0])

    assert not part.exists()
    assert other.exists()
