# Validation report — run_2 / persona D

Generated: 2026-06-07 18:20 UTC

**Run:** `run_2`
**Input:** `results/run_2`
**Output:** `results/validation/run_2`

Ground truth: `persona.json` (backstory ignored for scoring).

## Noah

Reconstruction: `result_noah.json`

**Overall embedding similarity:** 0.628481
**Unmatched counts:** processes missed=0, extra=0; steps missed=2, extra=0; exceptions missed=0, extra=0

### Process alignment (truth[1] ↔ recon[0], aggregate=0.94554)
- Step: "Check and Repair Hardware | tools: Diagnostic Tools | time: " ↔ "Check and repair the hardware | tools: diagnostic tools | ti" (sim=0.983883)
- Step: "Provide Repair Cost Calculation | tools:  | time: 45 minutes" ↔ "Provide repair cost calculation | tools:  | time: 45 minutes" (sim=0.982406)
- Step: "Check and Configure Software | tools: Configuration Software" ↔ "Check and configure the software | tools: configuration soft" (sim=0.980587)
- Step: "Test System Functionality | tools: Testing Software | time: " ↔ "Test the system functionality | tools: testing software | ti" (sim=0.95617)
- Step: "Billing | tools: Billing Software | time: 30 minutes | hando" ↔ "Handle the billing process | tools: billing software | time:" (sim=0.937332)
- Step: "Return Repaired Computer | tools:  | time: 20 minutes | hand" ↔ "Return the repaired computer to the customer | tools:  | tim" (sim=0.925208)
- Exception: "Unexpected hardware failure during testing. | Incr" ↔ "Unexpected hardware failure during testing | Incre" (sim=0.947958)

### Process alignment (truth[0] ↔ recon[1], aggregate=0.268208)
- Step: "Forward Process for Checking Pending Issues | tools:  | time" ↔ "Explain common issues and resolutions | tools:  | time:  | h" (sim=0.68698)
- Step: "CRA Opens Process in Sipac | tools: Sipac | time: 15 minutes" ↔ "Introduce new staff to key processes and tools | tools: Sipa" (sim=0.657789)
- Step: "Forward to Coordination | tools:  | time: 20 minutes | hando" ↔ "Guide them through specific steps of the processes | tools: " (sim=0.640503)
- Step: "Notify Approval | tools: Email | time: 10 minutes | handoff:" ↔ "Encourage questions and offer support | tools:  | time:  | h" (sim=0.583487)
- Step: "Enter in Academic System | tools: Academic System | time: 20" ↔ "Share tips and best practices | tools:  | time:  | handoff: " (sim=0.470573)
- Missed step: "Student Opens Ticket | tools: Sipac | time: 10 minutes | handoff: CRA"
- Missed step: "Notify Student About Pending Issues | tools: Email | time: 15 minutes | handoff:"
- Exception: "Student fails to provide necessary documents. | De" ↔ "New staff struggle with the learning curve of new " (sim=0.289198)

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 2 | The reconstruction fully captures the Computer Repair Workflow but omits the entire Student Ticket Management process and all its steps, leaving major activities missing. |
| Control Flow And Handoff Fidelity | 4 | For the Computer Repair Workflow, the sequence and handoffs match the ground truth; no control flow is provided for the missing Student Ticket Management process. |
| Attribute Accuracy | 5 | For the included steps, tools, durations, and handoff targets align closely with the ground truth, with only minor wording differences. |
| Exception And Edge Case Capture | 2 | It captures the exception for the Computer Repair Workflow but completely misses the Student Ticket Management exception. |
| Faithfulness No Hallucination | 1 | A non-existent 'mentoring new staff' process and its exception are introduced, which are not in the ground truth. |

## ElevenLabs

Reconstruction: `result_elevenlabs.json`

**Overall embedding similarity:** 0.607926
**Unmatched counts:** processes missed=0, extra=0; steps missed=2, extra=0; exceptions missed=1, extra=2

### Process alignment (truth[1] ↔ recon[1], aggregate=0.426665)
- Step: "Check and Repair Hardware | tools: Diagnostic Tools | time: " ↔ "Check and repair hardware | tools: diagnostic tools | time: " (sim=0.893523)
- Step: "Provide Repair Cost Calculation | tools:  | time: 45 minutes" ↔ "Calculate repair costs | tools:  | time:  | handoff: " (sim=0.817674)
- Step: "Test System Functionality | tools: Testing Software | time: " ↔ "Test system functionality | tools:  | time:  | handoff: " (sim=0.774665)
- Step: "Check and Configure Software | tools: Configuration Software" ↔ "Configure software | tools: configuration software | time:  " (sim=0.745704)
- Missed step: "Billing | tools: Billing Software | time: 30 minutes | handoff: Customer Service"
- Missed step: "Return Repaired Computer | tools:  | time: 20 minutes | handoff: "
- Missed exception: "Unexpected hardware failure during testing. | Increased repair time and potentia"

### Process alignment (truth[0] ↔ recon[0], aggregate=0.698673)
- Step: "Student Opens Ticket | tools: Sipac | time: 10 minutes | han" ↔ "Student opens a ticket in Sipac | tools: Sipac | time: about" (sim=0.948159)
- Step: "CRA Opens Process in Sipac | tools: Sipac | time: 15 minutes" ↔ "CRA opens the process in Sipac | tools: Sipac | time: around" (sim=0.947929)
- Step: "Notify Student About Pending Issues | tools: Email | time: 1" ↔ "Notify student about any pending issues via email | tools: e" (sim=0.906724)
- Step: "Forward to Coordination | tools:  | time: 20 minutes | hando" ↔ "Forward to coordination | tools:  | time: about 20 minutes |" (sim=0.864412)
- Step: "Forward Process for Checking Pending Issues | tools:  | time" ↔ "Check for pending issues | tools:  | time: about 30 minutes " (sim=0.857466)
- Step: "Enter in Academic System | tools: Academic System | time: 20" ↔ "Enter the process in the academic system | tools: academic s" (sim=0.848444)
- Step: "Notify Approval | tools: Email | time: 10 minutes | handoff:" ↔ "Send notification of approval by email | tools: email | time" (sim=0.835756)
- Exception: "Student fails to provide necessary documents. | De" ↔ "Missing documents, incomplete information, or disc" (sim=0.784243)
- Extra exception: "Bottlenecks when coordinating across departments | Happens about once every coup"
- Extra exception: "Manual duplicate data entry between Sipac and the academic system can introduce "

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 3 | All seven student-ticket steps are present, but the computer repair workflow omits the Billing and Return Repaired Computer steps (2 of 6 missing). |
| Control Flow And Handoff Fidelity | 2 | Several handoffs are incorrect or missing in the student process (e.g., pending-issues step not handed to Coordinator, coordination step handed to 'coordination' instead of Student, academic-system step lacks Coordinator handoff), and the repair process truncates before Billing and final return. |
| Attribute Accuracy | 2 | Many time fields are missing or only approximate, some tools are omitted (e.g., Testing Software), and multiple handoff targets are null or wrong compared to the ground truth. |
| Exception And Edge Case Capture | 2 | The missing-documents exception is captured (with added, non-required frequency details), but the repair workflow’s hardware-failure exception is missing and extra unrelated exceptions were introduced. |
| Faithfulness No Hallucination | 2 | It invents additional exceptions and frequency/impact details not in the ground truth, reducing precision, though no extra steps were added. |

---

*Embedding similarity uses greedy alignment by cosine similarity on field text. Judge scores are from a separate LLM comparison.*
