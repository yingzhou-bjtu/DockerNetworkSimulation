import json
from pypinyin import pinyin, Style

# 加载 JSON 文件
input_path = 'configs/static_topo.json'  # 请将此路径更改为你的 JSON 文件的路径
output_path = 'configs/static_topo_pinyin.json'

with open(input_path, 'r', encoding='utf-8') as file:
    data = json.load(file)

# 定义转换函数，将中文转换为数字拼音形式
def chinese_to_pinyin(text):
    pinyin_list = pinyin(text, style=Style.TONE3)
    return ''.join([item[0] for item in pinyin_list])

# 递归转换 JSON 中的所有中文内容
def convert_json_to_pinyin(obj):
    if isinstance(obj, dict):
        return {k: convert_json_to_pinyin(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_json_to_pinyin(element) for element in obj]
    elif isinstance(obj, str):  # 只处理字符串，假定可能为中文
        return chinese_to_pinyin(obj)
    else:
        return obj  # 若非字符串、列表或字典，则直接返回对象

# 执行转换
converted_data = convert_json_to_pinyin(data)

# 保存转换后的数据到新文件
with open(output_path, 'w', encoding='utf-8') as file:
    json.dump(converted_data, file, ensure_ascii=False, indent=4)

print(f"转换完成！已保存为 {output_path}")
