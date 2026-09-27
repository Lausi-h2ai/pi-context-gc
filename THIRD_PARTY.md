# Upstream projects

This repository contains the integration, benchmark, and analysis code. It does not bundle installed dependencies or model weights. The MIT license applies to original project material; upstream software and weights retain their respective terms.

- [Pi](https://github.com/earendil-works/pi): coding-agent SDK and provider runtime. Exact npm versions are in `package-lock.json`.
- [Laya](https://github.com/NandhaKishorM/laya): local retention worker; Python package `laya==0.3.20`, checkpoint `convaiinnovations/laya` at `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`.
- [Von](https://huggingface.co/wfzyx/von): optional local retention worker; Python package `von-sdk==1.2.3`, checkpoint `wfzyx/von` at `5df8185a4f2327ad0a7cd117cc4f701ac557b9ae`.

The Python workers download the configured checkpoints on first use. Review each upstream project's license and model terms before using or redistributing those components. Python environment versions from the original machine are recorded in `requirements.lock.txt`; that environment includes a platform-specific PyTorch/CUDA build.

The main coding model is remote and accessed through the user's own Pi subscription login. Access to that service and model is separate from this repository's license. This project is an independent experiment and is not an official Pi, Laya, Von, or OpenAI product.
