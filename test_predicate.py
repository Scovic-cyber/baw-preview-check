"""Self-test for preview_check.clean_preview.

Proves the fix against the EXACT previews rejected on 2026-11-10:
- the 3 real FEG claimFreeShare previews in fixtures/feg_claim_previews.json (parsedTx shape)
  must now pass;
- a Broccoli-shape preview (top-level to/from/value/inputData) must pass;
- a preview with a real risk, a reverting simulation, and a wrong-target
  preview must all fail.
Run before arming any timed fire script: python3 test_predicate.py
"""
import json, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from preview_check import clean_preview

CONTRACT = "0xb9d0CA9b63C564443AfE64B77ef91B3bA763e5f1"
WALLET = "0x9c3Cf8bF5FBAd888a0b7fAeD16313284061fe790"
DATA = "0x195ad114"

fails = []

# 1. Real FEG previews from 2026-11-10 — the ones wrongly rejected.
#    Extracted verbatim into fixtures/feg_claim_previews.json so this
#    test is self-contained (no live fire log needed).
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "feg_claim_previews.json")) as f:
    real = json.load(f)
print(f"real FEG previews found: {len(real)}")
for i, pj in enumerate(real, 1):
    ok = clean_preview(pj, CONTRACT, WALLET, DATA)
    print(f"  real preview {i}: clean={ok}")
    if not ok:
        fails.append(f"real FEG preview {i} should pass")

# 2. Broccoli-shape preview (top-level fields, empty risks object).
broccoli_shape = {
    "success": True,
    "data": {
        "requestId": "test-broccoli",
        "to": CONTRACT,
        "from": WALLET,
        "value": "0",
        "inputData": DATA,
        "requireConfirmation": False,
        "simulationResult": {"simulationCode": "000000000"},
        "risks": {"addresses": {}, "riskDetails": [], "riskBehaviors": []},
    },
}
ok = clean_preview(broccoli_shape, CONTRACT, WALLET, DATA)
print(f"  Broccoli-shape preview: clean={ok}")
if not ok:
    fails.append("Broccoli-shape preview should pass")

# 3. Dirty preview (real risk present) must fail.
dirty = json.loads(json.dumps(broccoli_shape))
dirty["data"]["risks"] = {"addresses": {}, "riskDetails": ["honeypot"], "riskBehaviors": []}
ok = clean_preview(dirty, CONTRACT, WALLET, DATA)
print(f"  dirty preview (risk present): clean={ok}")
if ok:
    fails.append("dirty preview should fail")

# 4. Reverting simulation must fail.
revert = json.loads(json.dumps(broccoli_shape))
revert["data"]["simulationResult"] = {"simulationCode": "123456789"}
ok = clean_preview(revert, CONTRACT, WALLET, DATA)
print(f"  reverting preview: clean={ok}")
if ok:
    fails.append("reverting preview should fail")

# 5. Wrong target contract must fail.
wrong = json.loads(json.dumps(broccoli_shape))
wrong["data"]["to"] = "0x0000000000000000000000000000000000000001"
ok = clean_preview(wrong, CONTRACT, WALLET, DATA)
print(f"  wrong-target preview: clean={ok}")
if ok:
    fails.append("wrong-target preview should fail")

# 6. Missing requestId must fail.
noreq = json.loads(json.dumps(broccoli_shape))
del noreq["data"]["requestId"]
ok = clean_preview(noreq, CONTRACT, WALLET, DATA)
print(f"  no-requestId preview: clean={ok}")
if ok:
    fails.append("no-requestId preview should fail")

# 7. Real Pocket Ai approve preview (typed parsedTx, no action field)
#    from 2026-11-10 — wrongly rejected before the typed-shape fix.
NFT = "0xf9D00B7a2992de00EBc5F9f04BAf95d44C542102"
MKT = "0xA044dD51f09A3D527B6bFCb4528095b647E4dd55"
APPROVE_DATA = (
    "0x095ea7b3"
    + "000000000000000000000000a044dd51f09a3d527b6bfcb4528095b647e4dd55"
    + "000000000000000000000000000000000000000000000000000000000000076c"
)
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "approve_preview_1900.json")) as f:
    approve_pj = json.load(f)
ok = clean_preview(approve_pj, NFT, WALLET, APPROVE_DATA)
print(f"  real Pocket Ai approve preview: clean={ok}")
if not ok:
    fails.append("real Pocket Ai approve preview should pass")

# 8. Same approve preview, wrong spender, must fail.
wrong_spender = json.loads(json.dumps(approve_pj))
wrong_spender["data"]["parsedTx"]["spender"] = "0x0000000000000000000000000000000000000001"
ok = clean_preview(wrong_spender, NFT, WALLET, APPROVE_DATA)
print(f"  approve preview, wrong spender: clean={ok}")
if ok:
    fails.append("approve preview with wrong spender should fail")

# 9. Same approve preview, wrong tokenId, must fail.
wrong_token = json.loads(json.dumps(approve_pj))
wrong_token["data"]["parsedTx"]["tokenId"] = "1901"
ok = clean_preview(wrong_token, NFT, WALLET, APPROVE_DATA)
print(f"  approve preview, wrong tokenId: clean={ok}")
if ok:
    fails.append("approve preview with wrong tokenId should fail")

# 10. Real Pocket Ai list preview (selector-only ContractInteraction)
#     from 2026-11-10 — wrongly rejected before the selector-shape fix.
LIST_DATA = "0x50fd7367" + format(1900, "064x") + format(4900000000000000, "064x")
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "list_preview_1900.json")) as f:
    list_pj = json.load(f)
ok = clean_preview(list_pj, MKT, WALLET, LIST_DATA)
print(f"  real Pocket Ai list preview: clean={ok}")
if not ok:
    fails.append("real Pocket Ai list preview should pass")

# 11. Same list preview, wrong selector in action, must fail.
wrong_sel = json.loads(json.dumps(list_pj))
wrong_sel["data"]["parsedTx"]["action"] = "0x00000000"
ok = clean_preview(wrong_sel, MKT, WALLET, LIST_DATA)
print(f"  list preview, wrong selector: clean={ok}")
if ok:
    fails.append("list preview with wrong selector should fail")

# 12. Same list preview, wrong contract, must fail.
wrong_contract = json.loads(json.dumps(list_pj))
wrong_contract["data"]["parsedTx"]["contractAddress"] = "0x0000000000000000000000000000000000000001"
ok = clean_preview(wrong_contract, MKT, WALLET, LIST_DATA)
print(f"  list preview, wrong contract: clean={ok}")
if ok:
    fails.append("list preview with wrong contract should fail")

if fails:
    print("FAIL:")
    for x in fails:
        print(" -", x)
    sys.exit(1)
print("ALL PASS")
