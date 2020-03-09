import os
import pyperf
import tempfile


def get_raw_values(filename, run_id):
    bench = pyperf.Benchmark.load(filename)
    run = bench.get_runs()[run_id]
    inner_loops = run.get_inner_loops()
    raw_values = [value * (loops * inner_loops)
                  for loops, value in run.warmups]
    total_loops = run.get_total_loops()
    raw_values.extend(value * total_loops for value in run.values)
    return (run, raw_values)


class Replay(object):
    def __init__(self, runner, filename):
        self.runner = runner
        self.args = runner.args
        self.filename = filename
        self.value_id = 0
        self.init()

    def init(self):
        args = runner.args
        self.run_id = self.args.first_run - 1
        if args.worker:
            self.read_session()

            run, self.raw_values = get_raw_values(self.filename, self.run_id)
            old_loops = args.loops
            args.loops = run.get_loops()
            if args.loops != old_loops:
                print("Set loops to %s: value from the JSON" % args.loops)
            # FIXME: handle inner_loops
            self.run_id += 1
            self.write_session()
        else:
            args.session_filename = tempfile.mktemp()
            self.write_session()

    def read_session(self):
        filename = self.args.session_filename
        if not filename:
            return
        with open(filename, "r") as fp:
            line = fp.readline()
        self.run_id = int(line.rstrip())

    def write_session(self):
        filename = self.args.session_filename
        if not filename:
            return
        with open(filename, "w") as fp:
            print(self.run_id, file=fp)
            fp.flush()

    def time_func(self, loops):
        raw_value = self.raw_values[self.value_id]
        self.value_id += 1
        return raw_value


def add_cmdline_args(cmd, args):
    cmd.append(args.filename)
    if args.session_filename:
        cmd.extend(('--session-filename', args.session_filename))


runner = pyperf.Runner(add_cmdline_args=add_cmdline_args)
runner.argparser.add_argument('filename')
runner.argparser.add_argument('--session-filename', default=None)
runner.argparser.add_argument('--first-run', type=int, default=1)

args = runner.parse_args()
replay = Replay(runner, args.filename)
runner.bench_time_func('bench', replay.time_func)
if not args.worker:
    os.unlink(args.session_filename)
