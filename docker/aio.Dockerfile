FROM myubuntu

COPY ./OSPF/src /app/ospf
COPY ./LISP /app/lisp
COPY ./socket /app/socket

# 在环境中编译
WORKDIR /app/ospf
RUN make clean
RUN make || true
RUN gcc -std=gnu99 -Wall -g -o ospf lsr.o recv.o hello.o lsdb.o io.o common.o spf.o nsm.o lsu.o main.o lsack.o dd.o send.o -lpthread

WORKDIR /app/lisp
RUN make
RUN make install

WORKDIR /app/socket
RUN make clean
RUN make

WORKDIR /app
