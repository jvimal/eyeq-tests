exptid=`date +%b%d-%H:%M`
dir=/tmp/$exptid/incast
time=60
n=1
P=4

ctrlc() {
	killall -9 python
	exit
}

trap ctrlc SIGINT

basecmd="python tests/scenario.py --time $time -n $n --run tcpvsudp --exptid $exptid"

for iso in "--enabled"; do
for size in 100G; do
	for proto in udp; do
		for mtu in 9000; do
            # WITH ISOLATION
			python tests/genconfig.py --type $proto --traffic incast \
				--size $size --repeat 1000 \
				--inter 5 -n $((n+2)) --time 1000 \
				--duration 100s \
				--tenant 2 > ~/vimal/exports/${n}to1_${size}_${proto}_tenant

			$basecmd --dir $dir/$proto-mtu$mtu-s$size-with$iso $iso \
				--traffic ~/vimal/exports/${n}to1_${size}_${proto}_tenant \
				--mtu $mtu \
				--ai 10 --md 4 \
				-P $P

            # WITHOUT ISOLATION
			#python tests/genconfig.py --type $proto --traffic incast \
			#	--size $size --repeat 1000 \
			#	--inter 5 -n 16 --time 1000 > ~/vimal/exports/14to1_${size}_${proto}

			#$basecmd --dir $dir/$proto-mtu$mtu-s$size-without \
			#	--traffic ~/vimal/exports/14to1_${size}_${proto} \
			#	--mtu $mtu
		done
	done
done
done

echo `date` $dir

pushd ../exptdata/$exptid

ext=pdf
for arg in "--accum 1000 -o plot-all.$ext" "--range 32.8:33.8 --accum 10 -o plot-zoom.$ext"; do
python2.6 ~/iso/tests/plots/plot_tenant_rate.py -f \
	udp-mtu9000-s100G-with--enabled/l1/tenant.txt --rx \
	--title "" $arg -l tcp udp
done

popd

echo udp ${n}to1 $dir >> TODO
