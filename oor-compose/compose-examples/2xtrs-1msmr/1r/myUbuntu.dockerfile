# 使用 Ubuntu 20.04 作为基础镜像
FROM ubuntu:focal

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

# 安装python包
RUN pip install scapy

# 设置启动命令
CMD ["/bin/bash"]