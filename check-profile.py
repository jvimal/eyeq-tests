
import argparse
import os
import pprint
from subprocess import Popen, PIPE
import pydoc
import termcolor as T
import re
import sys

parser = argparse.ArgumentParser(description="Perfiso perf summary from oprofile data.")

parser.add_argument('-d',
                    dest="d",
                    help="Directory containing the profile/ subdirectory.",
                    required=True)

parser.add_argument('-p',
                    dest="path",
                    help="Directory containing the modules.",
                    default="~/vimal/exports")

parser.add_argument('-a',
                    dest="annotate",
                    action="store_true",
                    help="Annotate source files instead of reporting.",
                    default=False)

parser.add_argument('-x',
                    dest="exclusive",
                    action="store_true",
                    help="Consider only perfiso files.",
                    default=False)

parser.add_argument('-g',
                    dest="grep",
                    nargs="+",
                    help="grep for pattern(s)",
                    default=[])

parser.add_argument('-e',
                    dest="event",
                    help="Event to report/annotate",
                    choices=["cycles","l1miss","llcmiss"],
                    default="cycles")

parser.add_argument('-t',
                    dest="thresh",
                    help="Lower overhead percent threshold to colour output",
                    type=float,
                    default=4.0)

parser.add_argument('-?',
                    dest="cmd",
                    help="Just print command",
                    action="store_true",
                    default=False)

parser.add_argument('--args',
                    dest="args",
                    help="Additional arguments",
                    default='')

args = parser.parse_args()
pat_spaces = re.compile(r'\s+')

CYAN="cyan"
GREY="grey"
GREEN="green"
YELLOW="yellow"
RED="red"
BOLD="bold"
PERFISO_FILES="direct.c,main.c,params.c,rc.c,rl.c,tx.c,vq.c,rl.h,tx.h,vq.h"

def filter_iso(line):
    if args.exclusive:
        return (line, (GREY, BOLD))
    if 'perfiso.ko' in line:
        return (line, CYAN)
    return (line, (GREY, BOLD))

def filter_annotate(line):
    if not args.annotate:
        return
    try:
        percent = pat_spaces.split(line.strip())[1]
        percent = float(percent)
    except:
        percent = 0.0

    if percent > 5*args.thresh:
        return (line, RED)
    if percent > 3*args.thresh:
        return (line, YELLOW)
    if percent > args.thresh:
        return (line, GREEN)
    return

def filter_grep(line):
    for pat in args.grep:
        if re.search(pat, line):
            return (line, CYAN)
    return

filters = [filter_iso, filter_annotate, filter_grep]

def do_filter(line):
    col = (GREY, BOLD)
    for f in filters:
        temp = f(line)
        if temp:
            line, col = temp
    return (line, col)

def filter_output(cmd):
    p = Popen(cmd, shell=True, stdout=PIPE)
    ret = ""
    for l in p.stdout.readlines():
        out, col = do_filter(l)
        attr = []
        if type(col) == tuple:
            col, attr = col
            attr = [attr]
        ret += T.colored(out, col, attrs=attr)
    return ret

def parse_dir(d):
    d = os.path.expanduser(d)
    d = os.path.join(d, "profile", "profile")
    exe = 'opreport'
    if args.annotate:
        exe = 'opannotate'
    cmd = "%s -p %s " % (exe, args.path)
    cmd += " -m all "
    cmd += " --session-dir %s " % d
    cmd += " session:profile "
    if args.event == "cycles":
        cmd += " event:CPU_CLK_UNHALTED "
    elif args.event == "l1miss":
        cmd += " event:L1D "
    elif args.event == "llcmiss":
        cmd += " event:LLC_MISS "
    if not args.annotate:
        cmd += " -a -l "
    else:
        cmd += " -s "
        cmd += ' -d ~/iso '
    cmd += ' %s ' % args.args
    if args.exclusive:
        if not args.annotate:
            cmd += " | egrep -i 'perfiso.ko'"
        else:
            cmd += " --include-file %s " % PERFISO_FILES

    if args.cmd:
        print cmd
    else:
        return pydoc.pipepager(filter_output(cmd), "less -R")

parse_dir(args.d)

