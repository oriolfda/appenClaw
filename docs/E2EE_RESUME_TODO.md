# E2EE Resume TODO (safe stop point)

Last updated: 2026-03-20 06:53 UTC
Branch: `feature/signal-e2ee-phase2`

## Safe-stop status
- Working tree clean at stop point.
- Latest pushed commits:
  - aigor-app: `ad08a40`
  - openclaw-app equivalent: `bd908ef`
- Current code remains functional with existing E2EE path.

## Real progress snapshot (recalculated)
1. Persistent DR session state model — DONE (100%)
2. Inbound decrypt using persistent `recvChainSeed` — IN PROGRESS (~45%)
3. Reply encrypt using persistent `sendChainSeed` — IN PROGRESS (~62%)
4. Per-message chain advancement — IN PROGRESS (~45%)
5. DH ratchet step over `rootKeySeed` — IN PROGRESS (~35%)
6. Header-based skipped cache usable (`headerId+counter`) — IN PROGRESS (~85%)
7. Persistence/recovery after restart — IN PROGRESS (~55%)
8. Strict checks/fallback policy — DONE (100%)
9. Final tests/validation — IN PROGRESS (~82%)

## Pending tasks (next exact order)
1) Finish inbound decrypt path to prioritize and advance `recvChainSeed` state per message.
2) Finish outbound reply encryption to prioritize and advance `sendChainSeed` state per message.
3) Complete DH ratchet root-key update lifecycle and controlled re-seeding.
4) Finish headerId+counter skipped-key retrieval/consumption path (not only storage).
5) Run final test matrix:
   - strict-mode plaintext rejection (`e2ee_required` / `e2ee_ciphertext_required` / `e2ee_attachment_required`)
   - replay reject
   - out-of-order within window
   - restart persistence continuity
   - attachment encrypted path

## Test evidence (2026-03-20 06:09 UTC)
- replay/out-of-order window check (`_ratchet_check_and_advance`) seq `1,3,2,3,4,2` => `T,T,T,F,T,F` (both bridges)
- restart continuity check => `counter1=True`, restart, `counter2=True`, replay `counter2=False`
- encrypted attachment decrypt path (`decrypt_e2ee_attachment`) => PASS
- headerId-isolated skipped validation check (`A1,A3,B2,A2`) => `T,T,F,T` (both bridges, no cross-header acceptance)
- repeatable smoke script `scripts/e2ee_headerid_smoke.py` sequence `A1,A3,B2,A2,A2(replay)` => `T,T,F,T,F` (both bridges)
- repeatable seed-persistence smoke script `scripts/e2ee_seed_progress_smoke.py` => `ok=true`, out counters `1,2`, recv/send chain counters `2,2` (both bridges)
- re-run smoke at 06:33 UTC: `e2ee_headerid_smoke.py` => `T,T,F,T,F`; `e2ee_seed_progress_smoke.py` => `ok=true` (both bridges)
- Android build check: `openclaw-app ./gradlew :app:assembleDebug` => BUILD SUCCESSFUL; `aigor-app ./gradlew :app:assembleRelease` => BUILD SUCCESSFUL
- recv-seed priority mix check (06:44 UTC): persistent `recvChainSeed` mixed before inbound per-message ratchet; smoke re-run OK (`e2ee_headerid_smoke.py` => `T,T,F,T,F`, `e2ee_seed_progress_smoke.py` => `ok=true`)
- send-seed priority check re-run (06:57 UTC): `e2ee_headerid_smoke.py` => `T,T,F,T,F`; `e2ee_seed_progress_smoke.py` => `{"ok":true,"outCounters":[1,2],"recvChainCounter":2,"sendChainCounter":2}` (both bridges)

## Resume checklist
- Confirm branch: `feature/signal-e2ee-phase2`
- Start with task (1)
- Commit in small slices (1 task = 1 commit)
- Build after each commit:
  - aigor-app: `./gradlew :app:assembleRelease`
  - openclaw-app: `./gradlew :app:assembleDebug`

## ETA (realistic)
- Remaining for block completion: ~2.5h to 4h
- Production hardening after that: +1 day
