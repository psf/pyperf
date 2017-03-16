import perf

runner = perf.Runner()
runner.timeit("sorted(list(range(1000)), key=lambda x: x)",
              "sorted(s, key=f)",
              "f = lambda x: x; s = list(range(1000))")
