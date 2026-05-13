# v1.0-rc Validation Test Manifest

| command | result | run_in_this_session | reason_if_not_run |
|---|---|---|---|
| .venv\Scripts\python.exe -m pytest -q tests/validation/test_v1_0_rc_freeze_readiness.py | PASS: 32 passed | True |  |
| .venv\Scripts\python.exe -m pytest -q tests/validation | PASS: 184 passed | True |  |
| .venv\Scripts\python.exe -m pytest -q tests/backtest/test_v1_0_horizon_policy.py tests/backtest/test_v1_0_simulation_run_manifest.py tests/backtest/test_v1_0_weight_config_loop.py tests/backtest/test_v1_0_layer_registry.py tests/backtest/test_v1_0_evaluation_evidence_v1.py tests/backtest/test_v1_0_selector_evaluator.py tests/backtest/test_v1_0_manual_review_packet.py | PASS: 119 passed | True |  |
| .venv\Scripts\python.exe -m pytest -q tests/backtest | PASS: 173 passed | True |  |
