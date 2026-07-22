#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip

python -m pip install \
  torch==2.12.1 \
  torchvision==0.27.1 \
  --index-url https://download.pytorch.org/whl/cu126
