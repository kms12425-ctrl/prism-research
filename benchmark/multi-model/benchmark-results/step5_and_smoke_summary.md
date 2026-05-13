# Benchmark Summary

Generated at: 2026-04-28T11:00:31.585182+00:00

## Smoke Baseline

| Scenario | Mean E2E (ms) | Request Tput (req/s) | Mean TTFT (ms) | Mean TPOT (ms) | Mean ITL (ms) |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline_1model | 4020.87 | 1.041 | 17.66 | 9.96 | 9.98 |
| baseline_2model | 3696.22 | 1.043 | 22.10 | 9.17 | 9.15 |

## Single Request

| Mode | Success | E2E (ms) | Server (ms) | TTFT (ms) | TPOT (ms) | Wait (ms) | Req Tput (req/s) | Error |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| static | yes | 392.05 | 386.60 | 76.20 | 9.70 | 3.20 | 2.551 | - |
| ours | yes | 304.80 | 298.78 | 13.27 | 9.21 | 2.49 | 3.281 | - |

## Notes

- Static single-request baseline was generated with benchmark/multi-model/model_configs/1_gpu_2_model_smoke_lowmem.json to fit the shared single A6000.
- Ours single-request artifact also succeeded on port 30034, so the summary now reflects a direct latency-vs-latency comparison.
