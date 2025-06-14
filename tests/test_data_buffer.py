from rl.data_buffer import DataBuffer


def test_memory_buffer_append_and_fetch() -> None:
    buf = DataBuffer()
    buf.append({"v": 1}, 0, 1.0)
    buf.append({"v": 2}, 1, -1.0)
    data = list(buf.fetch_all())
    assert len(data) == 2
    assert data[0][1] == 0
    assert data[1][2] == -1.0
