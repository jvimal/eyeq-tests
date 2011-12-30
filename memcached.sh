
dir=~/vimal/10g/exptdata/`date +%b%d-%H:%M`/memcached/
time=600

mkdir -p $dir

ctrlc() {
	killall -9 python
	exit
}

trap ctrlc SIGINT

for case in {1..5}; do
	python tests/scenario.py --run memcached --case $case --dir $dir --time $time
done

ssh l19 "for d in $dir/*; do echo \`basename \$d\` \`awk '/Period/ { s += \$4; n++; } END { print s/n }' \$d/memaslap.txt\`;   done"

echo "case  min  max  avg  std"
ssh l19 "for d in $dir/*; do echo \`basename \$d\` \`awk '/Total Statistics.*events/ { ok=1; }    /(Min|Max|Avg|Std):/ { if(ok==1) { printf \"%.2f   \",\$2 } } END { print }' \$d/memaslap.txt\`;  done"
