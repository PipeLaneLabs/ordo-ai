window.BENCHMARK_DATA = {
  "lastUpdate": 1770966402038,
  "repoUrl": "https://github.com/PipeLaneLabs/ordo-ai",
  "entries": {
    "Benchmark": [
      {
        "commit": {
          "author": {
            "email": "108556948+harmandeeppal@users.noreply.github.com",
            "name": "Harmandeep Pal",
            "username": "harmandeeppal"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "c052239be3bc8410f4d81c053c2465b430cd9537",
          "message": "Merge pull request #35 from PipeLaneLabs/staging\n\nci: enforce tiered branch promotion and unify semantic release + dynamic versioning",
          "timestamp": "2026-02-13T20:05:14+13:00",
          "tree_id": "2eb12d09ad6b235f081308c6b97177dbb30af71b",
          "url": "https://github.com/PipeLaneLabs/ordo-ai/commit/c052239be3bc8410f4d81c053c2465b430cd9537"
        },
        "date": 1770966401648,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/performance/test_benchmarks.py::test_agent_response_latency",
            "value": 5558.535795182706,
            "unit": "iter/sec",
            "range": "stddev: 0.0008122767961322436",
            "extra": "mean: 179.90349200713035 usec\nrounds: 1689"
          },
          {
            "name": "tests/performance/test_benchmarks.py::test_checkpoint_save_performance",
            "value": 3610963.6998796323,
            "unit": "iter/sec",
            "range": "stddev: 3.63547830761914e-8",
            "extra": "mean: 276.9343818198266 nsec\nrounds: 198413"
          },
          {
            "name": "tests/performance/test_benchmarks.py::test_budget_guard_check_performance",
            "value": 3886057.9943903037,
            "unit": "iter/sec",
            "range": "stddev: 5.29585968488294e-8",
            "extra": "mean: 257.33017917991555 nsec\nrounds: 194553"
          }
        ]
      }
    ]
  }
}