from scripts.convert_topology_to_pinyin import (
    convert_json_to_pinyin,
    resolve_topology_output_path,
)
from scripts.open_container_shells import build_terminal_command, parse_args
from scripts.quick_test import parse_args as parse_quick_test_args


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


def test_convert_topology_output_rejects_input_overwrite(tmp_path) -> None:
    input_path = tmp_path / "configs" / "topology.json"
    input_path.parent.mkdir()
    input_path.write_text("{}", encoding="utf-8")

    try:
        resolve_topology_output_path(input_path, input_path, project_root=tmp_path)
    except ValueError as exc:
        assert "must not overwrite" in str(exc)
    else:
        raise AssertionError("expected input overwrite to fail")


def test_convert_topology_output_rejects_non_json_suffix(tmp_path) -> None:
    input_path = tmp_path / "configs" / "topology.json"
    output_path = tmp_path / "configs" / "topology.txt"

    try:
        resolve_topology_output_path(input_path, output_path, project_root=tmp_path)
    except ValueError as exc:
        assert ".json" in str(exc)
    else:
        raise AssertionError("expected non-json output to fail")


def test_convert_topology_output_rejects_repo_root_output(tmp_path) -> None:
    input_path = tmp_path / "configs" / "topology.json"
    output_path = tmp_path / "converted.json"

    try:
        resolve_topology_output_path(input_path, output_path, project_root=tmp_path)
    except ValueError as exc:
        assert "configs/" in str(exc)
        assert "output/" in str(exc)
    else:
        raise AssertionError("expected repository-root output to fail")


def test_convert_topology_output_accepts_configs_output_and_external_paths(tmp_path) -> None:
    input_path = tmp_path / "configs" / "topology.json"
    configs_output = tmp_path / "configs" / "topology_pinyin.json"
    generated_output = tmp_path / "output" / "topology_pinyin.json"
    external_output = tmp_path.parent / f"{tmp_path.name}_topology_pinyin.json"

    assert resolve_topology_output_path(input_path, configs_output, project_root=tmp_path) == configs_output
    assert resolve_topology_output_path(input_path, generated_output, project_root=tmp_path) == generated_output
    assert resolve_topology_output_path(input_path, external_output, project_root=tmp_path) == external_output


def test_open_container_shells_requires_explicit_container_ids() -> None:
    args = parse_args(["node_1", "xtr_1"])

    assert args.container_ids == ["node_1", "xtr_1"]


def test_open_container_shells_passes_container_id_as_shell_argument() -> None:
    container_id = "node_1; touch /tmp/should_not_run"

    command = build_terminal_command(container_id)

    assert command[-1] == container_id
    assert container_id not in command[-3]


def test_quick_test_accepts_topology_overrides() -> None:
    args = parse_quick_test_args(
        ["--nodes", "6", "--msmr", "2", "--xtr-edge", "node_2:xtr_a"]
    )

    assert args.nodes == 6
    assert args.msmr == 2
    assert args.xtr_edge == [["node_2", "xtr_a"]]


def test_quick_test_rejects_too_small_topology() -> None:
    try:
        parse_quick_test_args(["--nodes", "2"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected --nodes 2 to fail")


def test_quick_test_rejects_xtr_edge_outside_generated_topology() -> None:
    try:
        parse_quick_test_args(["--nodes", "4", "--xtr-edge", "node_5:xtr_a"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected out-of-range router reference to fail")


def test_quick_test_rejects_duplicate_xtr_names() -> None:
    try:
        parse_quick_test_args(
            [
                "--nodes",
                "4",
                "--xtr-edge",
                "node_1:xtr_a",
                "--xtr-edge",
                "node_2:xtr_a",
            ]
        )
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected duplicate xTR names to fail")


def test_quick_test_rejects_xtr_name_that_collides_with_router() -> None:
    try:
        parse_quick_test_args(["--nodes", "4", "--xtr-edge", "node_1:node_2"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected xTR/router name collision to fail")
