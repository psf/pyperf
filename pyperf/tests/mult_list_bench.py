#!/usr/bin/env python3
import pyperf

runner = pyperf.Runner()
runner.timeit("[1]*1000",
              stmt="[1]*1000",
              duplicate=1024)
runner.timeit("[1,2]*1000",
              stmt="[1,2]*1000",
              duplicate=1024)
runner.timeit("[1,2,3]*1000",
              stmt="[1,2,3]*1000",
              duplicate=1024)
