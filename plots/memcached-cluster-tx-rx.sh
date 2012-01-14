
ops="set"
for op in $ops; do
plot_rate.py -f \
	memcached-mtu9000-iso--enable-work$op-6k.cnf-active{mem,udp,udp*mem}/l1/net.txt \
	-i total -l mem udp udp,mem --title "TX rates at server"

plot_rate.py -f \
	memcached-mtu9000-iso--enable-work$op-6k.cnf-active{mem,udp,udp*mem}/l5/net.txt \
	-i total -l mem udp udp,mem --title "TX rates at client"

plot_rate.py -f \
	memcached-mtu9000-iso--enable-work$op-6k.cnf-active{mem,udp,udp*mem}/l1/net.txt \
	-i total -l mem udp udp,mem --title "RX rates at server" --rx

plot_rate.py -f \
	memcached-mtu9000-iso--enable-work$op-6k.cnf-active{mem,udp,udp*mem}/l5/net.txt \
	-i total -l mem udp udp,mem --title "RX rates at client" --rx
done
