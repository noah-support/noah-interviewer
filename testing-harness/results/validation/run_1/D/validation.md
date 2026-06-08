# Validation report — run_1 / persona D

Generated: 2026-06-07 17:58 UTC

**Run:** `run_1`
**Input:** `results/run_1`
**Output:** `results/validation/run_1`

Ground truth: `persona.json` (backstory ignored for scoring).

## Noah

Reconstruction: `result_noah.json`

**Overall embedding similarity:** 0.75529
**Unmatched counts:** processes missed=0, extra=0; steps missed=0, extra=0; exceptions missed=0, extra=1

### Process alignment (truth[1] ↔ recon[1], aggregate=0.895168)
- Step: "Provide Repair Cost Calculation | tools:  | time: 45 minutes" ↔ "Provide repair cost calculation | tools:  | time: 45 minutes" (sim=0.974304)
- Step: "Check and Configure Software | tools: Configuration Software" ↔ "Check and configure the software | tools: configuration soft" (sim=0.973476)
- Step: "Check and Repair Hardware | tools: Diagnostic Tools | time: " ↔ "Check and repair the hardware | tools: diagnostic tools | ti" (sim=0.970332)
- Step: "Test System Functionality | tools: Testing Software | time: " ↔ "Test the system functionality | tools: testing software | ti" (sim=0.948534)
- Step: "Billing | tools: Billing Software | time: 30 minutes | hando" ↔ "Handle the billing process | tools: billing software | time:" (sim=0.931758)
- Step: "Return Repaired Computer | tools:  | time: 20 minutes | hand" ↔ "Return repaired computer to customer | tools:  | time:  | ha" (sim=0.828412)
- Exception: "Unexpected hardware failure during testing. | Incr" ↔ "Unexpected hardware failure during testing | Incre" (sim=0.969897)

### Process alignment (truth[0] ↔ recon[0], aggregate=0.629707)
- Step: "Notify Approval | tools: Email | time: 10 minutes | handoff:" ↔ "Notify approval | tools: email | time:  | handoff: " (sim=0.927833)
- Step: "Notify Student About Pending Issues | tools: Email | time: 1" ↔ "Notify student about pending issues | tools: email | time:  " (sim=0.919143)
- Step: "Forward Process for Checking Pending Issues | tools:  | time" ↔ "Check for pending issues | tools:  | time: 30 minutes | hand" (sim=0.894302)
- Step: "CRA Opens Process in Sipac | tools: Sipac | time: 15 minutes" ↔ "CRA opens the process in Sipac | tools: Sipac | time:  | han" (sim=0.88685)
- Step: "Student Opens Ticket | tools: Sipac | time: 10 minutes | han" ↔ "Open student ticket | tools: Sipac | time: 10 minutes | hand" (sim=0.872711)
- Step: "Enter in Academic System | tools: Academic System | time: 20" ↔ "Enter information into the academic system | tools:  | time:" (sim=0.844783)
- Step: "Forward to Coordination | tools:  | time: 20 minutes | hando" ↔ "Continue processing the ticket | tools:  | time:  | handoff:" (sim=0.479438)
- Exception: "Student fails to provide necessary documents. | De" ↔ "Students fail to provide the necessary documents |" (sim=0.882876)
- Extra exception: "The ticket remains stalled if the student doesn't send the necessary documents |"

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 4 | All repair workflow steps are present; in student ticket management, one ground-truth step (Forward to Coordination) is missing though most others appear. |
| Control Flow And Handoff Fidelity | 3 | Overall order is plausible, but several student-ticket handoffs are missing or incorrect (e.g., CRA to Coordinator, Notify Student to Student, Enter to Coordinator), and one routing step is absent; the repair workflow’s handoffs are correct. |
| Attribute Accuracy | 3 | Multiple student-ticket attributes are omitted or wrong (missing times for several steps, missing Academic System tool, several handoffs set to null), while the repair workflow matches closely except the final 20-minute duration. |
| Exception And Edge Case Capture | 5 | The key missing-documents exception is captured with proper impact and recovery, the repair exception matches, and an additional follow-up variant is included. |
| Faithfulness No Hallucination | 3 | A non-existent step ('Continue processing the ticket') and an extra exception were added, though most other details stay within the ground truth. |

## ElevenLabs

Reconstruction: `result_elevenlabs.json`

**Overall embedding similarity:** 0.769575
**Unmatched counts:** processes missed=1, extra=0; steps missed=0, extra=0; exceptions missed=0, extra=2

### Process alignment (truth[0] ↔ recon[0], aggregate=0.755128)
- Step: "Notify Student About Pending Issues | tools: Email | time: 1" ↔ "Notify student about any pending issues via email | tools: e" (sim=0.955863)
- Step: "Student Opens Ticket | tools: Sipac | time: 10 minutes | han" ↔ "Student opens a ticket in Sipac | tools: Sipac | time: 10 mi" (sim=0.954396)
- Step: "Forward Process for Checking Pending Issues | tools:  | time" ↔ "Forward the process for checking any pending issues | tools:" (sim=0.887385)
- Step: "CRA Opens Process in Sipac | tools: Sipac | time: 15 minutes" ↔ "CRA opens the process in Sipac | tools: Sipac | time: 15 min" (sim=0.872234)
- Step: "Forward to Coordination | tools:  | time: 20 minutes | hando" ↔ "Forward to coordination | tools:  | time: 20 minutes | hando" (sim=0.870426)
- Step: "Notify Approval | tools: Email | time: 10 minutes | handoff:" ↔ "Notify about approval through email | tools: email | time:  " (sim=0.833831)
- Step: "Enter in Academic System | tools: Academic System | time: 20" ↔ "Enter information into the academic system | tools: academic" (sim=0.833715)
- Exception: "Student fails to provide necessary documents. | De" ↔ "Missing documents or incorrect information from st" (sim=0.810408)
- Extra exception: "Delays from other departments during coordination | Impacts the overall process "
- Extra exception: "Unexpected technical issues with Sipac or other systems | Disruptive and slows d"
- Missed process: "Computer Repair Workflow"

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 2 | Includes all seven steps of the student ticket process but completely omits the Computer Repair Workflow and its steps. |
| Control Flow And Handoff Fidelity | 3 | The student ticket steps are in the correct order, but several handoffs are incorrect or missing (e.g., checking pending issues and entering info), reducing fidelity. |
| Attribute Accuracy | 2 | Tools largely match, but time_needed is missing for two steps and multiple handoff targets differ from ground truth; minor naming/casing inconsistencies remain. |
| Exception And Edge Case Capture | 2 | Captures the missing-documents exception for student tickets, but fails to include the repair workflow’s hardware failure exception. |
| Faithfulness No Hallucination | 2 | Introduces new exceptions (departmental delays, system issues) and extra recovery details not present in the ground truth, lowering precision. |

---

*Embedding similarity uses greedy alignment by cosine similarity on field text. Judge scores are from a separate LLM comparison.*
