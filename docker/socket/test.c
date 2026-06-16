import socket

# 服务器的IP地址和端口号
host = '0.0.0.0'  # 监听所有接口
port = 1235

# 创建一个socket对象
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 绑定IP地址和端口号
server_socket.bind((host, port))

# 开始监听，参数指定了队列中最多可有的连接数
server_socket.listen(5)

print(f"Listening on {host}:{port}")

try:
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
