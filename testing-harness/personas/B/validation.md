# Validation report — persona B

Generated: 2026-06-05 15:58 UTC

Ground truth: `persona.json` (backstory ignored for scoring).

## Noah

Reconstruction: `result_noah.json`

**Overall embedding similarity:** 0.414672
**Unmatched counts:** processes missed=0, extra=1; steps missed=5, extra=0; exceptions missed=0, extra=0

### Process alignment (truth[1] ↔ recon[1], aggregate=0.396986)
- Step: "Return_Computer_Without_Repair | tools:  | time: 10 minutes " ↔ "Calculate the repair costs if required | tools:  | time:  | " (sim=0.723705)
- Step: "Test_System_Functionality | tools: System Testing Suite | ti" ↔ "Run a series of tests using the System Testing Suite | tools" (sim=0.71844)
- Step: "Return_Repaired_Computer | tools:  | time: 10 minutes | hand" ↔ "Revisit the repair process if tests reveal an issue that was" (sim=0.688102)
- Step: "Billing | tools: Billing Software | time: 20 minutes | hando" ↔ "Complete the testing | tools:  | time:  | handoff: " (sim=0.600824)
- Missed step: "Check_and_Repair_Hardware | tools: Hardware Diagnostic Tool | time: 1 hour | han"
- Missed step: "Check_and_Configure_Software | tools: Software Configuration Utility | time: 1 h"
- Exception: "Billing software error | Inaccurate cost estimatio" ↔ "Tests might reveal an issue that wasn't fixed | Re" (sim=0.287113)

### Process alignment (truth[0] ↔ recon[0], aggregate=0.415003)
- Step: "Check_and_Repair_Hardware | tools: Hardware Diagnostic Tool " ↔ "Diagnose the issue and identify the specific part needed | t" (sim=0.621097)
- Step: "Provide_Repair_Cost_Calculation | tools: Billing Software | " ↔ "Place the order with the supplier | tools: inventory managem" (sim=0.51762)
- Missed step: "Return_Computer_Without_Repair | tools:  | time: 10 minutes | handoff: Provide_R"
- Missed step: "Check_and_Configure_Software | tools: Software Configuration Utility | time: 1 h"
- Missed step: "Test_System_Functionality | tools: System Testing Suite | time: 30 minutes | han"
- Exception: "Hardware component not available | Delays the repa" ↔ "Part might be out of stock with the supplier | Can" (sim=0.664839)
- Extra process: "Assisting with Billing Issues"

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 1 | The reconstructed process includes entirely different processes and steps not present in the ground truth. |
| Control Flow And Handoff Fidelity | 1 | The sequence and handoff chains in the reconstructed process do not match the ground truth processes. |
| Attribute Accuracy | 2 | Some tools and times are accurate, but many steps lack time details and incorrect tools are mentioned. |
| Exception And Edge Case Capture | 3 | Some exceptions are captured correctly, such as billing software errors, but others are invented or missing. |
| Faithfulness No Hallucination | 2 | The reconstructed process introduces new processes and steps not found in the ground truth, indicating hallucination. |

## ElevenLabs

Reconstruction: `result_elevenlabs.json`

**Overall embedding similarity:** 0.651095
**Unmatched counts:** processes missed=1, extra=0; steps missed=0, extra=0; exceptions missed=0, extra=1

### Process alignment (truth[0] ↔ recon[0], aggregate=0.637139)
- Step: "Provide_Repair_Cost_Calculation | tools: Billing Software | " ↔ "Calculating Repair Costs | tools: Billing Software | time: 1" (sim=0.929984)
- Step: "Check_and_Configure_Software | tools: Software Configuration" ↔ "Repairing Hardware or Software | tools: Software Configurati" (sim=0.798033)
- Step: "Check_and_Repair_Hardware | tools: Hardware Diagnostic Tool " ↔ "Diagnosing Issues | tools: Hardware Diagnostic Tool | time: " (sim=0.788632)
- Step: "Test_System_Functionality | tools: System Testing Suite | ti" ↔ "Testing System Functionality | tools: System Testing Suite |" (sim=0.766959)
- Step: "Return_Computer_Without_Repair | tools:  | time: 10 minutes " ↔ "Handling Billing | tools: Billing Software | time: 20 minute" (sim=0.530088)
- Exception: "Hardware component not available | Delays the repa" ↔ "Parts availability delays | Delays repair timeline" (sim=0.77214)
- Extra exception: "Billing software errors | Disrupts workflow and requires manual cost calculation"
- Missed process: "Extended Computer Repair Process"

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 2 | The reconstructed process misses some steps such as 'Return_Computer_Without_Repair' and 'Return_Repaired_Computer', and combines others, leading to incomplete coverage. |
| Control Flow And Handoff Fidelity | 1 | The sequence and handoffs are incorrect, as many steps in the reconstructed process have no handoffs and the order is not aligned with the ground truth. |
| Attribute Accuracy | 3 | While the tools and time_needed are mostly accurate, the handoff_to attributes are not correctly captured. |
| Exception And Edge Case Capture | 3 | The reconstructed process captures some exceptions correctly but adds unnecessary details and misses the recovery for 'Hardware component not available'. |
| Faithfulness No Hallucination | 2 | The reconstructed process introduces new steps like 'Diagnosing Issues' and 'Handling Billing' that are not present in the ground truth. |

---

*Embedding similarity uses greedy alignment by cosine similarity on field text. Judge scores are from a separate LLM comparison.*
