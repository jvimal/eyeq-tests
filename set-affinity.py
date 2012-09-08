import sys, os

dev = sys.argv[1]
mask = 1
count = 0

for line in open('/proc/interrupts').xreadlines():
    if dev not in line:
        continue
    nr = line.split(':')[0]
    nr = nr.strip()

    name = line.split(' ')[-1].strip()
    cmd = 'echo %d > /proc/irq/%s/smp_affinity' % (mask, nr)
    print name, cmd
    os.system(cmd)

    if count == 0:
        count += 1
        mask <<= 1
    else:
        if count % 2 == 0:
            mask <<= 1
        count += 1

