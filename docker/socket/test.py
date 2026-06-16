import socket

# 定义允许的IP范围
ip_prefix = '10.11.'
ip_range = range(21)  # 0-20范围
ip_suffix = '.1'  # 第四字段保持不变

# 服务器端口号
port = 1235

# 创建一个socket对象
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 设置允许地址复用
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# 依次尝试绑定IP范围的地址
try:
    for i in ip_range:
        host = f"{ip_prefix}{i}{ip_suffix}"  # 动态生成IP地址
        try:
            server_socket.bind((host, port))
            print(f"Bound to {host}:{port}")
            break  # 成功绑定后退出循环
        except Exception as e:
            print(f"Failed to bind to {host}:{port}: {e}")
    else:
        raise RuntimeError("Failed to bind to any IP address in the specified range.")
    
    # 开始监听，参数指定了队列中最多可有的连接数
    server_socket.listen(5)
    print(f"Listening on IP range {ip_prefix}0{ip_suffix}-{ip_prefix}20{ip_suffix}, port {port}")

    while True:
        # 建立客户端连接
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr} has been established.")

        # 接收数据
        message = client_socket.recv(1024).decode('utf-8')
        print(f"Received message: {message}")

        # 发送响应
        client_socket.send(b'Message received')

        # 关闭连接
        client_socket.close()
except KeyboardInterrupt:
    print("Server is shutting down.")
finally:
    server_socket.close()

