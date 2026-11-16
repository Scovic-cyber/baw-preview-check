"""Shared clean-preview check for baw contract-call previews.

Two lessons baked in (both cost the user a free mint on 2026-11-10):
- Broccoli: a preview risks object {"addresses": {}, "riskDetails": [],
  "riskBehaviors": []} means NO risks. Never treat the risks object itself
  as truthy = risky; clean means riskDetails AND riskBehaviors are empty.
- FEG: a clean preview does NOT always carry top-level to/from/value/
  inputData. That preview carried target + calldata only in
  parsedTx.contractAddress / parsedTx.action. Accept either shape, but
  require at least one positive address match AND one positive calldata
  match. from/value are checked only when present (the preview is built
  with --from/--value, so the simulation is already scoped to them).
- Pocket Ai list (2026-11-10): a clean approve preview carries NEITHER
  top-level inputData NOR parsedTx.action. It carries a TYPED parsedTx
  (transactionType "ApproveNft", contractAddress, spender, tokenId).
  Accept a typed parsedTx ONLY when every identifying field matches the
  calldata's own decoded args (selector + spender + tokenId) — a bare
  transactionType match is never enough.
- Pocket Ai list, same day: a plain ContractInteraction preview echoes
  ONLY the 4-byte selector in parsedTx.action (no args, no top-level
  inputData). The mint preview that landed exactly #1900 had this same
  shape, so a selector + contractAddress match is accepted for this
  shape — BUT it cannot echo the args, so the args must be verified
  independently: decode the calldata in the calling script and assert
  the args before previewing, and verify the resulting on-chain state
  after executing. Never execute a selector-only preview without both.

Every fire script must import this and pass test_predicate.py against a REAL
preview response before the window opens. A wrong predicate fails exactly
when speed matters most.
"""


def _typed_parsed_tx_matches(ptx, contract, data):
    """True only when a typed parsedTx (no `action` field) identifies the
    exact call in `data`. Each supported shape must match ALL of its
    identifying fields against the calldata's decoded args."""
    if not isinstance(ptx, dict) or not isinstance(data, str):
        return False
    if not data.startswith("0x") or len(data) < 10:
        return False
    sel = data[:10].lower()
    if (ptx.get("contractAddress") or "").lower() != contract.lower():
        return False
    if sel == "0x095ea7b3":  # approve(address spender, uint256 tokenId)
        if ptx.get("transactionType") != "ApproveNft":
            return False
        if len(data) < 10 + 128:
            return False
        spender = "0x" + data[10 + 24:10 + 64].lower()
        try:
            token_id = int(data[10 + 64:10 + 128], 16)
        except ValueError:
            return False
        return (
            (ptx.get("spender") or "").lower() == spender
            and str(ptx.get("tokenId")) == str(token_id)
        )
    return False


def clean_preview(pj, contract, wallet, data):
    """True only for a genuinely clean baw preview of `data` to `contract`
    from `wallet` with value 0. Missing/unverifiable fields fail closed."""
    if not isinstance(pj, dict):
        return False
    d = pj.get("data") or {}
    if pj.get("success") is not True or not d.get("requestId"):
        return False
    sim = d.get("simulationResult") or {}
    if sim.get("simulationCode") != "000000000":
        return False
    risks = d.get("risks") or {}
    if risks.get("riskDetails") != [] or risks.get("riskBehaviors") != []:
        return False
    if d.get("requireConfirmation") is True:
        return False
    ptx = d.get("parsedTx") or {}
    to_ok = ((d.get("to") or "").lower() == contract.lower()) or (
        (ptx.get("contractAddress") or "").lower() == contract.lower()
    )
    act_ok = ((d.get("inputData") or "").lower() == data.lower()) or (
        (ptx.get("action") or "").lower() == data.lower()
    ) or _typed_parsed_tx_matches(ptx, contract, data) or (
        # Selector-only ContractInteraction shape (see module docstring):
        # parsedTx.action echoes just the 4-byte selector. Accept only
        # when the selector AND the contract both match; the caller must
        # independently assert the calldata args before previewing and
        # verify the resulting on-chain state after executing.
        ptx.get("transactionType") == "ContractInteraction"
        and (ptx.get("action") or "").lower() == data[:10].lower()
        and (ptx.get("contractAddress") or "").lower() == contract.lower()
    )
    from_ok = ("from" not in d) or ((d.get("from") or "").lower() == wallet.lower())
    value_ok = ("value" not in d) or (str(d.get("value")) in ("0", "0x0"))
    return bool(to_ok and act_ok and from_ok and value_ok)
