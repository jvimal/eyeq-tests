
obj-m += tcp_bad.o

all:
	make -C /usr/src/linux-cfs-bw M=`pwd`
