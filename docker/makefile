# 定义镜像名称和 Dockerfile
AIO_IMAGE=aio
AIO_DOCKERFILE=aio.Dockerfile

UBUNTU_IMAGE=myubuntu
UBUNTU_DOCKERFILE=myubuntu.Dockerfile

# 默认目标，优先构建 myubuntu 镜像
all: ubuntu aio

# 构建 myubuntu 镜像
ubuntu:
	docker build -f $(UBUNTU_DOCKERFILE) -t $(UBUNTU_IMAGE) .

# 构建 aio 镜像
aio:
	docker build -f $(AIO_DOCKERFILE) -t $(AIO_IMAGE) .

# 清理构建的镜像
clean:
	docker rmi -f $(AIO_IMAGE) $(UBUNTU_IMAGE)

# 帮助信息
help:
	@echo "Makefile 使用说明:"
	@echo "make                 - 构建所有 Docker 镜像（先构建 myubuntu，后构建 aio）"
	@echo "make aio             - 构建 aio 镜像"
	@echo "make ubuntu          - 构建 myubuntu 镜像"
	@echo "make clean           - 删除所有构建的 Docker 镜像"
	@echo "make help            - 显示此帮助信息"

