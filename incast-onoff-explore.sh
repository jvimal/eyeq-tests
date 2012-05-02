exptid=`date +%b%d-%H:%M`
dir=/tmp/$exptid/incast-onoff-explore
time=30

ctrlc() {
	killall -9 python
	exit
}

trap ctrlc SIGINT

n=3

basecmd="python tests/scenario.py --time $time -n $n --run tcpvsudp --exptid $exptid"

for onoff in 10ms,20ms; do
for iso in "--enable"; do
	for proto in udp; do
		for mtu in 9000; do
			python tests/genconfig.py --type $proto --traffic incast \
				--size 100G --repeat -1 \
				--on-off $onoff -n $n --time 1000 \
				--start 10 \
				--tenant 2 > ~/vimal/exports/${n}to1_${proto}_${onoff}_tenant

			for ai in 10 20 30; do
			for md in 1 4 8; do

			$basecmd --dir $dir/$proto-mtu$mtu-$onoff-n$n-with$iso-ai$ai-md$md $iso \
				--traffic ~/vimal/exports/${n}to1_${proto}_${onoff}_tenant \
				--mtu $mtu \
				--ai $ai \
				--md $md \

			done
			done

			# WITHOUT ISOLATION
			#python tests/genconfig.py --type $proto --traffic incast \
			#--size 100G --repeat -1 \
			#	--on-off $onoff -n $n --time 1000 \
			#	> ~/vimal/exports/${n}to1_${proto}_${onoff}

			#$basecmd --dir $dir/$proto-mtu$mtu-$onoff-n$n-without \
			#	--traffic ~/vimal/exports/${n}to1_${proto}_${onoff} \
			#	--mtu $mtu
		done
	done
done
done

echo `date` $dir

pushd ../exptdata/$exptid
for dir in *; do
	python2.6 ~/iso/tests/plots/plot_tenant_rate.py -f $dir/l1/tenant.txt \
		--rx --accum 200 -o $dir/rate.png \
		-l tcp udp

	python2.6 ~/iso/tests/plots/plot_tenant_rate.py -f $dir/l3/tenant.txt \
		--tx -o $dir/udp.png -l tcp udp \
		--range 21.0:21.1
done
popd

echo incast scenario exploration $exptid >> TODO
