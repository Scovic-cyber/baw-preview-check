# baw-preview-check

A fail-closed verifier for Binance Agentic Wallet (`baw`) contract-call
previews. One function, `clean_preview()`, answers a single question before
you sign or execute anything:

> **Is this preview genuinely a clean, value-0 call to exactly the contract
> and calldata I intend — with a passing simulation and no risk flags?**

It was written after the same naive check cost two free NFT mints in one
day (10 Nov 2026): once by misreading an *empty* risks object as risky, and
once by demanding address fields that the preview shape does not carry. Both
failures happened in timed windows, where a wrong predicate fails exactly
when speed matters most. This module is the shared, tested replacement — and
every fire script that uses it must pass `test_predicate.py` against a real
preview before its window opens.

## The four clean preview shapes

`baw contract-call preview` does not return one stable shape. All four of
these are clean when everything else checks out:

1. **Top-level shape** — `to` / `from` / `value` / `inputData` at the top
   of `data`. (Broccoli mint.)
2. **parsedTx shape** — target + calldata only in
   `parsedTx.contractAddress` / `parsedTx.action`. No top-level fields.
   (FEG free-share claim.)
3. **Typed parsedTx shape** — no `action` at all; a typed parsedTx such as
   `ApproveNft` with `spender` + `tokenId`. Accepted **only** when every
   identifying field matches the calldata's own decoded args. A bare
   `transactionType` match is never enough.
4. **Selector-only shape** — a plain `ContractInteraction` preview echoes
   only the 4-byte selector in `parsedTx.action` (no args, no top-level
   `inputData`). Accepted on selector + contract match — **but** the preview
   cannot echo the args, so the caller must decode and assert the calldata
   args *before* previewing, and verify the resulting on-chain state
   *after* executing. Never execute a selector-only preview without both.

## What counts as clean

`clean_preview(preview_json, contract, wallet, calldata)` returns `True`
only when **all** of these hold:

- `success` is `true` and a `requestId` is present (preview IDs expire
  after ~5 minutes — re-preview, don't reuse);
- `simulationResult.simulationCode` is `"000000000"`;
- `risks.riskDetails` **and** `risks.riskBehaviors` are both empty lists
  (an empty `risks` object itself means *no* risks — never treat the
  object as truthy);
- `requireConfirmation` is not `true`;
- the target matches: top-level `to` **or** `parsedTx.contractAddress`
  equals the intended contract;
- the calldata matches: top-level `inputData` **or** `parsedTx.action`
  equals the intended calldata, **or** the typed-parsedTx check passes,
  **or** the selector-only check passes;
- `from`, when present, equals the wallet; `value`, when present, is `0`.

Anything missing or unverifiable **fails closed** (`False`). A clean
preview is not a guarantee: on-chain state can change between preview and
execution, so always verify the resulting state afterwards, and stop and
notify a human on any execution failure instead of retrying blindly.

## Usage

```python
from preview_check import clean_preview

preview = ...  # parsed JSON from `baw contract-call preview --json`
if clean_preview(preview, contract, wallet, calldata):
    # execute via `baw contract-call execute --requestId <id>`
    ...
else:
    # STOP. Do not execute, do not retry with a different call.
    ...
```

## Tests

```sh
python3 test_predicate.py
```

12 checks, all against real preview responses captured 10 Nov 2026
(`fixtures/`): the 3 FEG previews that were wrongly rejected, the Broccoli
shape, the real Pocket Ai approve + list previews — plus negative cases
(risk present, reverting simulation, wrong target, missing requestId,
wrong spender, wrong tokenId, wrong selector, wrong contract), which must
all fail.

## Scope

This checks *previews*, not contracts. It does not audit the target
contract, check honeypots, or judge whether a mint is worth doing. Verify
the contract, supply, and eligibility separately before you preview.

## License

MIT. See `LICENSE`.
