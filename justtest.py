import subprocess

container_ids = ["4bf875d3a0fb", "5d2b5d4a1c45", "6e3c3d2a6d7d"]

# 打开多个终端，每个终端执行 docker exec 命令并设置不同的标题
for container_id in container_ids:
    subprocess.run(['gnome-terminal', '--title', container_id, '--', 'bash', '-c', f"docker exec -it {container_id} bash; exec bash"])
