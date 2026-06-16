# 使用基础镜像，这里以 alpine 为例，因为它体积小
FROM ubuntu:latest

# 更新包列表并安装必要的软件
RUN apt-get update && \
    apt-get install -y \
    net-tools \
    iputils-ping \
    iproute2 \
    iperf3 \
    traceroute \
    python3 \
    python3-pip \
    vim

# 将二进制文件复制到镜像中
WORKDIR /app
COPY ospf /app/myapp

# 使二进制文件可执行
# RUN chmod +x /usr/local/bin/app

# 定义容器启动时执行的命令
CMD ["./myapp"]
