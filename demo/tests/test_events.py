from common.events import Event, write_event, read_events, merge_key_runs


def test_jsonl_roundtrip(tmp_path):
    write_event(str(tmp_path),
                Event(index=0, t=0.1, type="click", x=1, y=2, button="left"))
    write_event(str(tmp_path), Event(index=1, t=0.5, type="key", key="a"))
    evs = read_events(str(tmp_path))
    assert len(evs) == 2
    assert evs[0].type == "click" and evs[0].x == 1
    assert evs[1].key == "a"


def _key(i, t, ch):
    return Event(index=i, t=t, type="key", key=ch)


def test_merge_text_run():
    evs = [_key(0, 0.0, "h"), _key(1, 0.2, "i"),
           Event(index=2, t=0.4, type="key", key="enter")]
    out = merge_key_runs(evs)
    assert out[0].text == "hi" and out[0].type == "key"
    assert out[1].key == "enter"


def test_merge_includes_spaces():
    evs = [_key(0, 0.0, "h"), _key(1, 0.1, " "), _key(2, 0.2, "i")]
    out = merge_key_runs(evs)
    assert out[0].text == "h i"


def test_merge_breaks_on_gap():
    evs = [_key(0, 0.0, "a"), _key(1, 3.0, "b")]
    out = merge_key_runs(evs)
    assert [e.text for e in out] == ["a", "b"]


def test_merge_keeps_clicks_between():
    evs = [_key(0, 0.0, "a"),
           Event(index=1, t=0.1, type="click", x=5, y=5),
           _key(2, 0.2, "b")]
    out = merge_key_runs(evs)
    assert len(out) == 3
    assert out[0].text == "a" and out[1].type == "click" and out[2].text == "b"
