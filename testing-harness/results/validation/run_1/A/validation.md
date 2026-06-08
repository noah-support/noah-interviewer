# Validation report — run_1 / persona A

Generated: 2026-06-07 17:49 UTC

**Run:** `run_1`
**Input:** `results/run_1`
**Output:** `results/validation/run_1`

Ground truth: `persona.json` (backstory ignored for scoring).

## Noah

Reconstruction: `result_noah.json`

**Overall embedding similarity:** 0.631277
**Unmatched counts:** processes missed=0, extra=0; steps missed=5, extra=3; exceptions missed=0, extra=2

### Process alignment (truth[0] ↔ recon[0], aggregate=0.791409)
- Step: "Forward Process for Checking Pending Issues | tools: Sipac |" ↔ "Forward for checking pending issues | tools: Sipac | time: 2" (sim=0.933108)
- Step: "Enter in Academic System | tools: Academic System | time: 20" ↔ "Enter details into the Academic System | tools: Academic Sys" (sim=0.930901)
- Step: "Notify Student About Pending Issues | tools: Email | time: 1" ↔ "Notify the student about any pending matters | tools: email " (sim=0.897209)
- Step: "CRA Opens Process in Sipac | tools: Sipac | time: 30 minutes" ↔ "CRA team opens the process in Sipac | tools: Sipac | time:  " (sim=0.884051)
- Step: "Student Opens Ticket | tools: Sipac | time: 15 minutes | han" ↔ "Open a ticket | tools: Sipac | time: 15 minutes | handoff: C" (sim=0.853293)
- Step: "Notify Approval | tools: Email | time: 10 minutes | handoff:" ↔ "Notify the Approval Team via email | tools: email | time:  |" (sim=0.809745)
- Extra step: "Recover the ticket after resubmission | tools: ticketing system | time:  | hando"
- Extra step: "Update the ticket in Sipac | tools: Sipac | time:  | handoff: "
- Exception: "Incorrect ticket information | Delays in processin" ↔ "Incorrect ticket information | Delays processing |" (sim=0.985357)
- Extra exception: "Delay in receiving correct information | Slows down the entire process and affec"

### Process alignment (truth[1] ↔ recon[1], aggregate=0.536953)
- Step: "Forward Complaint Internally | tools: Internal Communication" ↔ "Forward the complaint internally | tools: internal communica" (sim=0.880897)
- Step: "New Complaint Received | tools: Complaint System | time: 15 " ↔ "Receive a new complaint in the Complaint System | tools: Com" (sim=0.874535)
- Step: "Inform Complainant | tools: Email | time: 10 minutes | hando" ↔ "Inform the complainant via email | tools: email | time:  | h" (sim=0.847445)
- Step: "Open a New Case | tools: Case Management Software | time: 30" ↔ "Open a case in the case management software | tools: case ma" (sim=0.827589)
- Step: "Receive References | tools: Reference Database | time: 1 hou" ↔ "Receive references for verification | tools:  | time:  | han" (sim=0.826913)
- Step: "Confirm External Reference | tools: Verification System | ti" ↔ "Update the records after confirming the external reference |" (sim=0.725504)
- Extra step: "Confirm references | tools:  | time:  | handoff: "
- Exception: "Missing reference documents | Verification delays " ↔ "Missing reference documents | Causes verification " (sim=0.957849)
- Extra exception: "Missing reference documents still unavailable | Slows down the entire process un"

### Process alignment (truth[2] ↔ recon[2], aggregate=0.463777)
- Missed step: "Open | tools: Incident Management System | time: 10 minutes | handoff: Assignmen"
- Missed step: "Assignment | tools: Incident Management System | time: 15 minutes | handoff: Res"
- Missed step: "Operator Update | tools: Communication Platform | time: 30 minutes | handoff: Qu"
- Missed step: "Status Change | tools: Incident Management System | time: 10 minutes | handoff: "
- Missed step: "Closed | tools: Incident Management System | time: 5 minutes | handoff: "
- Exception: "Status not updated correctly | Miscommunication on" ↔ "Incorrect ticket information | Usually causes dela" (sim=0.402529)

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 2 | Student Ticket Handling and Complaint Management include most expected steps, but all five Incident Resolution steps are missing entirely. This creates a major recall gap despite partial coverage in the first two processes. |
| Control Flow And Handoff Fidelity | 2 | Multiple handoffs are incorrect or omitted (e.g., CRA to Coordinator, Notify Student to Student, and nearly all Complaint Management handoffs), and extra steps disrupt the intended sequence. With Incident Resolution absent, the overall flow integrity is weak. |
| Attribute Accuracy | 2 | Several micro-details are missing or wrong: many time fields are blank, tools are omitted or misplaced (e.g., Reference Database and Verification System not used where expected), and key handoffs are incorrect or null. |
| Exception And Edge Case Capture | 2 | The core exceptions for Student Tickets and Complaints are captured, but the Incident Resolution exception is missing and replaced with an unrelated one, and extra non-GT exceptions were added. |
| Faithfulness No Hallucination | 2 | There are multiple invented elements, including extra steps (ticket recovery/update, records update), additional exceptions, a wrong exception for Incident Resolution, and an unspecified 'ticketing system'. |

## ElevenLabs

Reconstruction: `result_elevenlabs.json`

**Overall embedding similarity:** 0.435048
**Unmatched counts:** processes missed=0, extra=0; steps missed=10, extra=0; exceptions missed=1, extra=1

### Process alignment (truth[0] ↔ recon[0], aggregate=0.454668)
- Step: "Student Opens Ticket | tools: Sipac | time: 15 minutes | han" ↔ "Check new student tickets | tools: Sipac | time:  | handoff:" (sim=0.739745)
- Step: "Notify Student About Pending Issues | tools: Email | time: 1" ↔ "Request resubmission of correct information from students wh" (sim=0.727279)
- Step: "Forward Process for Checking Pending Issues | tools: Sipac |" ↔ "Coordinate with teams to ensure process steps are followed |" (sim=0.642648)
- Missed step: "CRA Opens Process in Sipac | tools: Sipac | time: 30 minutes | handoff: Coordina"
- Missed step: "Enter in Academic System | tools: Academic System | time: 20 minutes | handoff: "
- Missed step: "Notify Approval | tools: Email | time: 10 minutes | handoff: "
- Exception: "Incorrect ticket information | Delays in processin" ↔ "Incorrect ticket information from students | Cause" (sim=0.871341)
- Extra exception: "Missing reference documents | Delays the process | Ask students to provide the n"

### Process alignment (truth[1] ↔ recon[1], aggregate=0.425644)
- Step: "New Complaint Received | tools: Complaint System | time: 15 " ↔ "Check new complaints | tools: Complaint System | time:  | ha" (sim=0.789922)
- Step: "Forward Complaint Internally | tools: Internal Communication" ↔ "Coordinate with teams to ensure process steps are followed |" (sim=0.689715)
- Missed step: "Open a New Case | tools: Case Management Software | time: 30 minutes | handoff: "
- Missed step: "Receive References | tools: Reference Database | time: 1 hour | handoff: Verific"
- Missed step: "Confirm External Reference | tools: Verification System | time: 45 minutes | han"
- Missed step: "Inform Complainant | tools: Email | time: 10 minutes | handoff: "
- Missed exception: "Missing reference documents | Verification delays | Contact external sources for"

### Process alignment (truth[2] ↔ recon[2], aggregate=0.454281)
- Step: "Closed | tools: Incident Management System | time: 5 minutes" ↔ "Review logs and update incident statuses manually when neede" (sim=0.734926)
- Step: "Assignment | tools: Incident Management System | time: 15 mi" ↔ "Coordinate with teams on incident progress | tools: Email, i" (sim=0.692704)
- Missed step: "Open | tools: Incident Management System | time: 10 minutes | handoff: Assignmen"
- Missed step: "Operator Update | tools: Communication Platform | time: 30 minutes | handoff: Qu"
- Missed step: "Status Change | tools: Incident Management System | time: 10 minutes | handoff: "
- Exception: "Status not updated correctly | Miscommunication on" ↔ "Miscommunication about incident progress and statu" (sim=0.801394)

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 2 | Majority of ground-truth steps across all three processes are missing; the reconstruction collapses detailed multi-step flows into a few high-level actions and omits key activities like case opening, forwarding, reference handling, assignment, and closure. |
| Control Flow And Handoff Fidelity | 1 | The sequence and handoffs (e.g., Student → CRA → Coordinator → Approval teams) are not represented; most handoffs are null and the structured chains in the ground truth are lost. |
| Attribute Accuracy | 2 | Some tools match (Sipac, Email, Complaint System, Incident Management System), but times are omitted and handoffs are largely absent; the addition of generic 'internal communication tools' is imprecise relative to the specified tools. |
| Exception And Edge Case Capture | 2 | It captures the incorrect ticket info and the incident status-update exception, but misses the complaint 'missing references' exception and misassigns 'missing reference documents' to the student tickets process. |
| Faithfulness No Hallucination | 2 | It introduces generic coordination steps and an extra exception under student tickets, and adds impact/frequency details not in the ground truth, indicating hallucinated content. |

---

*Embedding similarity uses greedy alignment by cosine similarity on field text. Judge scores are from a separate LLM comparison.*
