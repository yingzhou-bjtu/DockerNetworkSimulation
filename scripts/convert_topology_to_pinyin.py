import argparse
import json
from pathlib import Path


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


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Convert Chinese strings in a topology JSON file to pinyin.")
    parser.add_argument("--input", type=Path, default=Path("configs/static_topo.json"))
    parser.add_argument("--output", type=Path, default=Path("configs/static_topo_pinyin.json"))
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    data = json.loads(args.input.read_text(encoding="utf-8"))
    converted_data = convert_json_to_pinyin(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(converted_data, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )
    print(f"Converted topology JSON written to {args.output}")


if __name__ == "__main__":
    main()
