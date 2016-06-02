import json

import perf


class Results:
    def __init__(self, runs=None, name=None, metadata=None, formatter=None):
        if runs is not None:
            self.runs = runs
        else:
            self.runs = []
        self.name = name
        # Raw metadata dictionary, key=>value, keys and values are non-empty
        # strings
        if metadata is not None:
            self.metadata = metadata
        else:
            self.metadata = {}
        if formatter is not None:
            self._formatter = formatter
        else:
            self._formatter = perf._format_run_result

    def format(self, verbose=False):
        if self.runs:
            values = []
            first_run = self.runs[0]
            warmup = first_run.warmup
            samples = len(first_run.values) - warmup
            loops = first_run.loops
            for run in self.runs:
                # FIXME: handle the case where final values is empty
                values.extend(run.values[run.warmup:])
                if loops is not None and run.loops != loops:
                    loops = None
                run_samples = len(run.values) - run.warmup
                if samples is not None and samples != run_samples:
                    samples = None
                if warmup is not None and warmup != run.warmup:
                    warmup = None

            iterations = []
            nrun = len(self.runs)
            if nrun > 1:
                iterations.append(perf._format_number(nrun, 'run'))
            if samples:
                text = perf._format_number(samples, 'sample')
                if verbose and warmup:
                    text = '%s (warmup: %s)' % (text, warmup)
                iterations.append(text)
            if loops:
                iterations.append(perf._format_number(loops, 'loop'))

            text = self._formatter(values, verbose)
            if iterations:
                text = '%s: %s' % (' x '.join(iterations), text)
        else:
            text = '<no run>'
        if self.name:
            text = '%s: %s' % (self.name, text)
        return text

    def __str__(self):
        return self.format()


class RunResult:
    def __init__(self, values=None, loops=None, warmup=0, formatter=None):
        if (values is not None
        and any(not(isinstance(value, float) and value >= 0)
                for value in values)):
            raise TypeError("values must be a list of float >= 0")
        if not(loops is None or (isinstance(loops, int) and loops >= 0)):
            raise TypeError("loops must be an int >= 0 or None")
        if not(isinstance(warmup, int) or warmup >= 0):
            raise TypeError("warmup must be an int >= 0")

        self.values = []
        if values is not None:
            self.values.extend(values)
        self.loops = loops
        self.warmup = warmup
        if formatter is not None:
            self._formatter = formatter
        else:
            self._formatter = perf._format_run_result

    def format(self, verbose=False):
        values = self.values[self.warmup:]
        return self._formatter(values, verbose)

    def __str__(self):
        return self.format()

    @classmethod
    def from_json(cls, text):
        data = json.loads(text)
        if 'run_result' not in data:
            raise ValueError("JSON doesn't contain run_result")
        data = data['run_result']

        version = data.get('version', '')
        if version != 1:
            raise ValueError("version %r not supported" % version)

        values = data['values']
        warmup = data['warmup']
        loops = data.get('loops', None)
        return cls(values=values, loops=loops, warmup=warmup)

    def json(self):
        data = {'version': 1, 'values': self.values, 'warmup': self.warmup}
        if self.loops is not None:
            data['loops'] = self.loops
        # FIXME: export formatter
        return json.dumps({'run_result': data})
