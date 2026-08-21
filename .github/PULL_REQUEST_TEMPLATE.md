## What this changes

One or two sentences. What is different afterwards, and why it needed to be.

## How it was checked

Paste the output rather than describing it. A claim that the tests pass is not
evidence that they did.

```text
```

- [ ] `ruff format --check .` and `ruff check .` are clean
- [ ] `mypy` reports nothing
- [ ] Every test file runs, and coverage is 100% of statements and branches
- [ ] `conformance/hardware.test.py` still holds every figure to the manual

## If this changes how a header is read

Run the census over a library you own and paste what it found. A change that
leaves every test passing and moves the number of cartridges this package
agrees with is still a regression.

## If this changes an access count

Say where the figure comes from. Two of the three are derived from bus speeds
Nintendo printed, and the derivation is shown in `conformance/hardware.json`. The
third is marked unverified on purpose. Moving one from unverified to verified
needs a passage in Book I or Book II, or a measurement on real hardware, not
another implementation that agrees.

## What it does not carry

- [ ] No cartridge, no fragment of one, and no digest fine enough to rebuild one
- [ ] Nothing that says where to obtain them
