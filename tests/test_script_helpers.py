from scripts.convert_topology_to_pinyin import convert_json_to_pinyin
from scripts.open_container_shells import build_terminal_command, parse_args


def test_convert_json_to_pinyin_preserves_structure() -> None:
    payload = {
        "nodes": ["北京", "node_2"],
        "meta": {"region": "海淀"},
        "count": 2,
    }

    assert convert_json_to_pinyin(payload) == {
        "nodes": ["bei3jing1", "node_2"],
        "meta": {"region": "hai3dian4"},
        "count": 2,
    }


def test_open_container_shells_requires_explicit_container_ids() -> None:
    args = parse_args(["node_1", "xtr_1"])

    assert args.container_ids == ["node_1", "xtr_1"]


def test_open_container_shells_passes_container_id_as_shell_argument() -> None:
    container_id = "node_1; touch /tmp/should_not_run"

    command = build_terminal_command(container_id)

    assert command[-1] == container_id
    assert container_id not in command[-3]
