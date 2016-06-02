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
            warmup = len(first_run.warmups)
            nrun = len(first_run.values)
            loops = first_run.loops
            for run in self.runs:
                # FIXME: handle the case where values is empty
                values.extend(run.values)
                if loops is not None and run.loops != loops:
                    loops = None
                run_nrun = len(run.values)
                if nrun is not None and nrun != run_nrun:
                    nrun = None
                run_warmup = len(run.warmups)
                if warmup is not None and warmup != run_warmup:
                    warmup = None

            iterations = []
            nprocess = len(self.runs)
            if nprocess > 1:
                iterations.append(perf._format_number(nprocess, 'process', 'processes'))
            if nrun:
                text = perf._format_number(nrun, 'run')
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
    def __init__(self, values=None, warmups=None, loops=None, formatter=None):
        if not(loops is None or (isinstance(loops, int) and loops >= 0)):
            raise TypeError("loops must be an int >= 0 or None")
        if (values is not None
        and any(not(isinstance(value, float) and value >= 0)
                for value in values)):
            raise TypeError("values must be a list of float >= 0")
        if (warmups is not None
        and any(not(isinstance(value, float) and value >= 0)
                for value in warmups)):
            raise TypeError("warmups must be a list of float >= 0")

        self.values = []
        if values is not None:
            self.values.extend(values)
        self.loops = loops
        self.warmups = []
        if warmups is not None:
            self.warmups.extend(warmups)
        if formatter is not None:
            self._formatter = formatter
        else:
            self._formatter = perf._format_run_result

    def format(self, verbose=False):
        return self._formatter(self.values, verbose)

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
        warmups = data['warmups']
        loops = data.get('loops', None)
        return cls(loops=loops, values=values, warmups=warmups)

    def json(self):
        data = {'version': 1, 'values': self.values, 'warmups': self.warmups}
        if self.loops is not None:
            data['loops'] = self.loops
        # FIXME: export formatter
        return json.dumps({'run_result': data})
