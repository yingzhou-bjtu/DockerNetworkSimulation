# 编译器和编译选项
CC = gcc
CFLAGS = -Wall -g
LDFLAGS =

# 可执行文件名
TARGET1 = udp_forward
TARGET2 = send_to_yoyo

# 源文件和目标文件
SRCS1 = udp_forward.c cJSON.c
SRCS2 = send_to_yoyo.c
OBJS1 = $(SRCS1:.c=.o)
OBJS2 = $(SRCS2:.c=.o)

# 默认目标
all: $(TARGET1) $(TARGET2)

# 生成 udp_forward 可执行文件
$(TARGET1): $(OBJS1)
	$(CC) $(CFLAGS) -o $@ $^

# 生成 send_to_yoyo 可执行文件
$(TARGET2): $(OBJS2)
	$(CC) $(CFLAGS) -o $@ $^

# 编译源文件为目标文件
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# 清理生成的文件
clean:
	rm -f $(TARGET1) $(TARGET2) $(OBJS1) $(OBJS2)

