#!/bin/bash
set -e

CONFIGS=(
    "configs/exp_condB_prefix_only.yaml"
    "configs/exp_condC_icl_only.yaml"
    "configs/exp_condD_baseline.yaml"
)

for cfg in "${CONFIGS[@]}"; do
    echo "========================================"
    echo "Running: $cfg"
    echo "========================================"
    python start_try.py --config_file "$cfg"
    echo ""
done

echo "All conditions done."
