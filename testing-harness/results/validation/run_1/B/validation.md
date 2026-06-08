# Validation report — run_1 / persona B

Generated: 2026-06-07 17:51 UTC

**Run:** `run_1`
**Input:** `results/run_1`
**Output:** `results/validation/run_1`

Ground truth: `persona.json` (backstory ignored for scoring).

## Noah

Reconstruction: `result_noah.json`

**Overall embedding similarity:** 0.374514
**Unmatched counts:** processes missed=0, extra=1; steps missed=3, extra=0; exceptions missed=0, extra=0

### Process alignment (truth[1] ↔ recon[1], aggregate=0.345419)
- Step: "Return_Repaired_Computer | tools:  | time: 10 minutes | hand" ↔ "Prepare to return the computer to the customer | tools:  | t" (sim=0.747531)
- Step: "Return_Computer_Without_Repair | tools:  | time: 10 minutes " ↔ "Calculate the repair costs if required | tools:  | time:  | " (sim=0.725259)
- Step: "Billing | tools: Billing Software | time: 20 minutes | hando" ↔ "Complete the testing | tools:  | time: 30 minutes | handoff:" (sim=0.679271)
- Step: "Test_System_Functionality | tools: System Testing Suite | ti" ↔ "Run a series of tests using the System Testing Suite | tools" (sim=0.651727)
- Step: "Check_and_Repair_Hardware | tools: Hardware Diagnostic Tool " ↔ "Revisit the repair process if tests reveal an issue that was" (sim=0.590646)
- Missed step: "Check_and_Configure_Software | tools: Software Configuration Utility | time: 1 h"
- Exception: "Billing software error | Inaccurate cost estimatio" ↔ "Tests might reveal an issue that wasn't fixed | Re" (sim=0.287113)

### Process alignment (truth[0] ↔ recon[0], aggregate=0.384154)
- Step: "Check_and_Repair_Hardware | tools: Hardware Diagnostic Tool " ↔ "Diagnose the issue and identify the specific part needed | t" (sim=0.631729)
- Step: "Provide_Repair_Cost_Calculation | tools: Billing Software | " ↔ "Place the order with the supplier | tools: inventory managem" (sim=0.531023)
- Step: "Return_Computer_Without_Repair | tools:  | time: 10 minutes " ↔ "Inform the customer about the expected delay and keep them u" (sim=0.422157)
- Missed step: "Check_and_Configure_Software | tools: Software Configuration Utility | time: 1 h"
- Missed step: "Test_System_Functionality | tools: System Testing Suite | time: 30 minutes | han"
- Exception: "Hardware component not available | Delays the repa" ↔ "Part might be out of stock with the supplier | Can" (sim=0.664127)
- Extra process: "Assisting with Billing Issues"

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 2 | The reconstruction omits multiple core steps (e.g., Return_Computer_Without_Repair, Check_and_Repair_Hardware, Check_and_Configure_Software, Return_Repaired_Computer) and does not reflect the two defined processes; it only partially covers testing and cost calculation. |
| Control Flow And Handoff Fidelity | 1 | Handoffs are mostly absent (set to null) and the sequence does not mirror either ground-truth chain (e.g., no consistent Provide_Repair_Cost_Calculation sink or Billing→Testing→Return path). |
| Attribute Accuracy | 2 | Where there is overlap, a few details match (System Testing Suite and ~30 minutes; billing software and 15 minutes), but many attributes are missing or incorrect (times omitted, wrong tools introduced, and handoffs not captured). |
| Exception And Edge Case Capture | 4 | It captures both key exceptions (part unavailable and billing software error) with plausible recoveries, though wording varies; it also adds an extra testing-related exception not in the ground truth. |
| Faithfulness No Hallucination | 1 | The reconstruction introduces non-existent processes and tools (e.g., Ordering Parts, inventory management system, diagnose/prepare/revisit steps) and alters structure beyond the ground truth. |

## ElevenLabs

Reconstruction: `result_elevenlabs.json`

**Overall embedding similarity:** 0.656605
**Unmatched counts:** processes missed=1, extra=0; steps missed=0, extra=0; exceptions missed=0, extra=1

### Process alignment (truth[1] ↔ recon[0], aggregate=0.614379)
- Step: "Billing | tools: Billing Software | time: 20 minutes | hando" ↔ "Handle billing | tools: Billing Software | time: around 20 m" (sim=0.853116)
- Step: "Return_Repaired_Computer | tools:  | time: 10 minutes | hand" ↔ "Perform hardware repairs | tools:  | time: about an hour | h" (sim=0.808531)
- Step: "Test_System_Functionality | tools: System Testing Suite | ti" ↔ "Test system functionality | tools: System Testing Suite | ti" (sim=0.769879)
- Step: "Check_and_Configure_Software | tools: Software Configuration" ↔ "Perform software configuration | tools: Software Configurati" (sim=0.767578)
- Step: "Check_and_Repair_Hardware | tools: Hardware Diagnostic Tool " ↔ "Diagnose issues on received computers | tools: Hardware Diag" (sim=0.759761)
- Step: "Return_Computer_Without_Repair | tools:  | time: 10 minutes " ↔ "Calculate repair costs | tools:  | time: about 15 minutes | " (sim=0.726389)
- Exception: "Billing software error | Inaccurate cost estimatio" ↔ "Billing software errors | Disrupts the workflow an" (sim=0.758761)
- Extra exception: "Parts not available or delayed updates from the parts procurement team about ava"
- Missed process: "Computer Repair Process"

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 3 | Core activities (hardware repair, software config, testing, cost calculation, billing) are present, but key steps like Return_Computer_Without_Repair and Return_Repaired_Computer are missing. The two distinct processes were merged into one. |
| Control Flow And Handoff Fidelity | 2 | No handoffs are provided and the sequence deviates from the ground truth, especially around billing vs. testing order. The structured flows leading to Provide_Repair_Cost_Calculation are not represented. |
| Attribute Accuracy | 3 | Times largely align (1 hour, 30 minutes, 15/20 minutes), and most tools match for software config, testing, and billing. However, the hardware repair step omits the diagnostic tool and cost calculation lacks the Billing Software; handoff targets are absent. |
| Exception And Edge Case Capture | 3 | Billing software error is captured with the correct manual recovery. Parts unavailability is noted, but the recovery omits ordering and informing the customer, weakening fidelity. |
| Faithfulness No Hallucination | 3 | An extra 'diagnose issues' step and added impact metrics (hours per week, procurement delays) are introduced beyond the ground truth. While mostly aligned, these additions constitute mild hallucinations. |

---

*Embedding similarity uses greedy alignment by cosine similarity on field text. Judge scores are from a separate LLM comparison.*
