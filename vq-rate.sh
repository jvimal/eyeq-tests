
dir=~/vimal/10g/exptdata/`date +%b%d-%H:%M`/vq-rate
time=120

ctrlc() {
	killall -9 python
	exit
}

trap ctrlc SIGINT

basecmd="python tests/scenario.py --time $time --run tcpvsudp"

size=100G
proto=udp
# WITH ISOLATION
python tests/genconfig.py --type $proto --traffic incast \
	--size $size --repeat 1000 \
	--inter 5 -n 16 --time 1000 \
	--tenant 2 > ~/vimal/exports/14to1_${size}_${proto}_tenant

for vqrate in 8000 8500 8800 9000 9200 9400 9600 9800 10000; do
for mtu in 1500 9000; do
for n in 1 2 4 8 14; do
	subdir=mtu$mtu-vq${vqrate}-n$n
	echo $basecmd -n $n --dir $dir/$subdir --enable \
		--traffic ~/vimal/exports/14to1_${size}_${proto}_tenant \
		--mtu $mtu --vqrate $vqrate
done
done
done

echo `date` $dir
