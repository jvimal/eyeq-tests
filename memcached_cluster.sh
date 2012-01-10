
time=300

ctrlc() {
  killall -9 python
  exit
}

trap ctrlc SIGINT
size=1G
dirs=""
exptid=`date +%b%d-%H:%M`

# Vary mtu
# Vary workloads
# With and Without isolation

python tests/genconfig.py --traffic fullmesh \
	--size $size --type udp --inter 10 -n 16 --time $time \
	-P 1 \
	--tenant 2 > ~/vimal/exports/loadfiles/fullmesh_n16_udp_tenant_2_${size}

python tests/genconfig.py --traffic fullmesh \
	--size $size --type udp --inter 10 -n 16 --time $time \
	-P 1 \
	> ~/vimal/exports/loadfiles/fullmesh_n16_udp_${size}

# Both tenants executed alone without interference

for mtu in 9000; do
	for iso in "" "--enable"; do
		for workload in ~/vimal/exports/memcached_cluster/*; do
			for active in udp mem udp,mem; do
				work=`basename $workload`
				dir=/tmp/memcached-mtu$mtu-iso$iso-work$work-active$active
				mkdir -p $dir
				dirs="$dirs\n$dir"

				traffic=fullmesh_n16_udp_${size}
				if [[ $iso = "--enable" ]]; then
					traffic=fullmesh_n16_udp_tenant_2_${size}
				fi

				echo $exptid $dir $workload $iso $mtu $traffic $active > $dir/README;

				python tests/test_memcached_cluster.py --ns 4 --nc 12 $iso \
					--dir $dir \
					--time $time \
					--mtu $mtu \
					--memaslap $workload \
					--exptid $exptid \
					--traffic ~/vimal/exports/loadfiles/$traffic \
					--active $active
			done
		done
	done
done

echo `date` $exptid
echo -e $dirs
