
time=300

ctrlc() {
  killall -9 python
  exit
}

trap ctrlc SIGINT
size=10G
dirs=""
exptid=`date +%b%d-%H:%M`

# Just the effect of EyeQ on an overloaded memcached
for mtu in 9000; do
	for iso in "" "--enable"; do
		for workload in ~/vimal/exports/memcached_cluster/set-20k.cnf; do
			for active in mem; do
				work=`basename $workload`
				dir=/tmp/memcached-mtu$mtu-iso$iso-work$work-active$active
				mkdir -p $dir
				dirs="$dirs\n$dir"

				traffic=fullmesh_n16_udp_${size}
				if [[ $iso = "--enable" ]]; then
					traffic=fullmesh_n16_udp_tenant_2_${size}
				fi

				echo memcached overload $exptid $dir $workload $iso $mtu $traffic $active > $dir/README.txt;

				python tests/test_memcached_cluster.py --ns 4 --nc 12 $iso \
					--dir $dir \
					--time $time \
					--mtu $mtu \
					--memaslap $workload \
					--exptid $exptid \
					--traffic ~/vimal/exports/loadfiles/$traffic \
					--active $active
				    #--mcperf --mcsize 6000 --mcrate 3000 --mcexp --nconn 10
			done
		done
	done
done

pushd ../exptdata/$exptid
for workload in ~/vimal/exports/memcached_cluster/set-20k.cnf; do
for ext in png pdf; do
    work=`basename $workload`;
    echo $work
    mkdir -p graphs/$ext;

	# Use this for memaslap
	files=memaslap.txt
	extra=""

	# Use this for mcperf
	#files="mcperf-0-*.txt mcperf-1-*.txt mcperf-2-*.txt mcperf-3-*.txt"
	#extra="--mcperf"

	for file in $files; do
		echo $file
		python2.6 ~/iso/tests/plots/plot-memcached-stats.py -f \
			memcached-mtu9000-iso--enable-work$work-activemem/l5/$file \
			memcached-mtu9000-iso-work$work-activemem/l5/$file \
			--legend mem  mem+EyeQ  \
			-o graphs/$ext/$work-$file.$ext $extra;
	done

    # RX/TX rates for one server/client for mem and mem,udp active tenants
    for tenants in mem; do
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
popd

echo memcached_cluster_overload $exptid >> TODO
