# Contributing

Useful next work includes a deterministic archiving control under the same eligibility and budget rules, repeated trials with balanced arm order, and new tasks evaluated with a frozen policy.

Install Node.js 24 and Python 3.12, then run the local checks:

```bash
npm ci
npm run check
npm test
python3 -m unittest discover -s benchmarks/general-analysis -p 'test_*.py'
python3 benchmarks/general-evaluate-test.py
```

These checks use local fixtures and judge doubles, without subscription requests or model downloads. Running the actual benchmark separately requires dependencies and authentication described in the README and consumes the user's model quota.

Keep benchmark protocol changes separate from interpretation of previously recorded runs. Use a fresh output directory whenever pinned implementation or design changes. Include failed tasks in reports, distinguish cached from uncached input, and report quality alongside token savings.
