import argparse
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_OUTPUT_DIRS = ("configs", "output")


def path_is_relative_to(path, parent):
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def chinese_to_pinyin(text):
    from pypinyin import Style, pinyin

    pinyin_list = pinyin(text, style=Style.TONE3)
    return ''.join([item[0] for item in pinyin_list])


def convert_json_to_pinyin(obj):
    if isinstance(obj, dict):
        return {k: convert_json_to_pinyin(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_json_to_pinyin(element) for element in obj]
    if isinstance(obj, str):
        return chinese_to_pinyin(obj)
    return obj


def build_parser():
    parser = argparse.ArgumentParser(description="Convert Chinese strings in a topology JSON file to pinyin.")
    parser.add_argument("--input", type=Path, default=Path("configs/static_topo.json"))
    parser.add_argument("--output", type=Path, default=Path("configs/static_topo_pinyin.json"))
    return parser


def parse_args(argv=None):
    return build_parser().parse_args(argv)


def resolve_topology_output_path(input_path, output_path, project_root=PROJECT_ROOT):
    resolved_input = input_path.resolve(strict=False)
    resolved_output = output_path.resolve(strict=False)

    if output_path.exists() and output_path.is_dir():
        raise ValueError("--output must be a JSON file path, not a directory")
    if resolved_output.suffix.lower() != ".json":
        raise ValueError("--output must use a .json suffix")
    if resolved_output == resolved_input:
        raise ValueError("--output must not overwrite --input")

    resolved_project_root = project_root.resolve(strict=False)
    if path_is_relative_to(resolved_output, resolved_project_root):
        allowed_dirs = [
            (resolved_project_root / dirname).resolve(strict=False)
            for dirname in REPOSITORY_OUTPUT_DIRS
        ]
        if not any(path_is_relative_to(resolved_output, directory) for directory in allowed_dirs):
            allowed = ", ".join(f"{dirname}/" for dirname in REPOSITORY_OUTPUT_DIRS)
            raise ValueError(f"--output inside the repository must be under {allowed}")

    return resolved_output


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        output_path = resolve_topology_output_path(args.input, args.output)
    except ValueError as exc:
        parser.error(str(exc))

    data = json.loads(args.input.read_text(encoding="utf-8"))
    converted_data = convert_json_to_pinyin(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(converted_data, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )
    print(f"Converted topology JSON written to {output_path}")


if __name__ == "__main__":
    main()
