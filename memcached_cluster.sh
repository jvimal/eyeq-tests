
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
	--size $size --type udp --inter 16 -n 16 --time $time \
	-P 1 \
	--tenant 2 > ~/vimal/exports/loadfiles/fullmesh_n16_udp_tenant_2_${size}

python tests/genconfig.py --traffic fullmesh \
	--size $size --type udp --inter 16 -n 16 --time $time \
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
					--nconn 16 \
					--active $active \
					--mcperf --mcsize 6000 --mcrate 6000 --mcexp
			done
		done
	done
done

pushd ../exptdata/$exptid
for workload in ~/vimal/exports/memcached_cluster/*; do
for ext in png pdf; do
    work=`basename $workload`;
    echo $work
    mkdir -p graphs/$ext;

	# Use this for memaslap
	files=memaslap.txt
	extra=""

	# Use this for mcperf
	files="mcperf-0-*.txt mcperf-1-*.txt mcperf-2-*.txt mcperf-3-*.txt"
	extra="--mcperf"

	for file in $files; do
		echo $file
		python2.6 ~/iso/tests/plots/plot-memcached-stats.py -f \
			memcached-mtu9000-iso--enable-work$work-activemem/l5/$file \
			memcached-mtu9000-iso--enable-work$work-activeudp,mem/l5/$file \
			memcached-mtu9000-iso-work$work-activeudp,mem/l5/$file \
			--legend mem udp,mem+EyeQ udp,mem-without-EyeQ \
			-o graphs/$ext/$work-$file.$ext $extra;
	done

    # RX/TX rates for one server/client for mem and mem,udp active tenants
    for tenants in mem udp,mem; do
      python2.6 ~/iso/tests/plots/plot_tenant_rate.py \
          --files memcached-mtu9000-iso--enable-work$work-active$tenants/l1/tenant.txt \
          -o graphs/$ext/rate$work-server-$tenants.$ext -l mem udp

      python2.6 ~/iso/tests/plots/plot_tenant_rate.py \
          --files memcached-mtu9000-iso--enable-work$work-active$tenants/l5/tenant.txt \
          -o graphs/$ext/rate$work-client-$tenants.$ext -l mem udp
    done
done
done

echo `date` $exptid
echo -e $dirs

