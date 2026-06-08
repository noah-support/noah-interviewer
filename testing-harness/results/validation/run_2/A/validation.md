# Validation report — run_2 / persona A

Generated: 2026-06-07 18:11 UTC

**Run:** `run_2`
**Input:** `results/run_2`
**Output:** `results/validation/run_2`

Ground truth: `persona.json` (backstory ignored for scoring).

## Noah

Reconstruction: `result_noah.json`

**Overall embedding similarity:** 0.732973
**Unmatched counts:** processes missed=0, extra=2; steps missed=1, extra=0; exceptions missed=0, extra=0

### Process alignment (truth[0] ↔ recon[0], aggregate=0.727431)
- Step: "Notify Student About Pending Issues | tools: Email | time: 1" ↔ "Notify the student about pending issues | tools: email | tim" (sim=0.922853)
- Step: "CRA Opens Process in Sipac | tools: Sipac | time: 30 minutes" ↔ "CRA team opens the process in Sipac | tools: Sipac | time: 3" (sim=0.918304)
- Step: "Forward Process for Checking Pending Issues | tools: Sipac |" ↔ "Forward the process for checking pending issues in Sipac | t" (sim=0.894976)
- Step: "Student Opens Ticket | tools: Sipac | time: 15 minutes | han" ↔ "Open a ticket | tools: Sipac | time: 15 minutes | handoff: C" (sim=0.853293)
- Step: "Notify Approval | tools: Email | time: 10 minutes | handoff:" ↔ "Check for pending issues | tools:  | time: 30 minutes | hand" (sim=0.653952)
- Missed step: "Enter in Academic System | tools: Academic System | time: 20 minutes | handoff: "
- Exception: "Incorrect ticket information | Delays in processin" ↔ "Incorrect ticket information | Delays processing |" (sim=0.953933)

### Process alignment (truth[1] ↔ recon[1], aggregate=0.811672)
- Step: "Receive References | tools: Reference Database | time: 1 hou" ↔ "Receive references from the reference database | tools: refe" (sim=0.94331)
- Step: "Confirm External Reference | tools: Verification System | ti" ↔ "Confirm external references | tools: verification system | t" (sim=0.931168)
- Step: "New Complaint Received | tools: Complaint System | time: 15 " ↔ "Receive a new complaint | tools: Complaint System | time: 15" (sim=0.902783)
- Step: "Forward Complaint Internally | tools: Internal Communication" ↔ "Forward the case internally | tools: internal communication " (sim=0.854503)
- Step: "Inform Complainant | tools: Email | time: 10 minutes | hando" ↔ "Inform the complainant about the outcome | tools: email | ti" (sim=0.823088)
- Step: "Open a New Case | tools: Case Management Software | time: 30" ↔ "Open a new case | tools:  | time:  | handoff: " (sim=0.822363)
- Exception: "Missing reference documents | Verification delays " ↔ "Missing reference documents | Delays verification " (sim=0.965711)

### Process alignment (truth[2] ↔ recon[2], aggregate=0.685993)
- Step: "Status Change | tools: Incident Management System | time: 10" ↔ "Change the status of the incident in the Incident Management" (sim=0.89547)
- Step: "Closed | tools: Incident Management System | time: 5 minutes" ↔ "Close the incident | tools:  | time: 5 minutes | handoff: " (sim=0.876039)
- Step: "Assignment | tools: Incident Management System | time: 15 mi" ↔ "Open an incident in the Incident Management System | tools: " (sim=0.861805)
- Step: "Operator Update | tools: Communication Platform | time: 30 m" ↔ "Update the operator using a communication platform | tools: " (sim=0.787156)
- Step: "Open | tools: Incident Management System | time: 10 minutes " ↔ "Assign to the resolution team | tools:  | time: 15 minutes |" (sim=0.713937)
- Exception: "Status not updated correctly | Miscommunication on" ↔ "Status isn't updated correctly | Leads to miscommu" (sim=0.926136)
- Extra process: "process optimization"
- Extra process: "coordination"

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 4 | Most ground-truth steps are represented across the three processes; only the 'Enter in Academic System' and 'Notify Approval' steps are missing from Student Ticket Handling. |
| Control Flow And Handoff Fidelity | 2 | Several handoffs are wrong or omitted (e.g., Student notification not handed to the student; Incident 'Open' should go to Assignment Team; 'Operator Update' should go to QA) and an extra 'Check for pending issues' step alters the intended flow. |
| Attribute Accuracy | 2 | Many micro-details are incorrect or missing: tools omitted (e.g., Case Management Software, Incident Management System), times missing or wrong (e.g., 2 hours reduced to 30 minutes), and multiple handoff targets mis-specified. |
| Exception And Edge Case Capture | 5 | Exceptions for all three core processes closely match the ground truth in what goes wrong, impact, and recovery. |
| Faithfulness No Hallucination | 2 | The reconstruction hallucinates two entire processes ('process optimization', 'coordination') and adds an extra step not in the ground truth. |

## ElevenLabs

Reconstruction: `result_elevenlabs.json`

**Overall embedding similarity:** 0.60805
**Unmatched counts:** processes missed=0, extra=0; steps missed=9, extra=0; exceptions missed=0, extra=0

### Process alignment (truth[0] ↔ recon[0], aggregate=0.586979)
- Step: "Student Opens Ticket | tools: Sipac | time: 15 minutes | han" ↔ "Monitor status of open student tickets | tools: Sipac | time" (sim=0.791994)
- Step: "Forward Process for Checking Pending Issues | tools: Sipac |" ↔ "Coordinate student tickets by forwarding cases and checking " (sim=0.70668)
- Step: "Notify Student About Pending Issues | tools: Email | time: 1" ↔ "Communicate with students as needed | tools: email, internal" (sim=0.695304)
- Missed step: "CRA Opens Process in Sipac | tools: Sipac | time: 30 minutes | handoff: Coordina"
- Missed step: "Enter in Academic System | tools: Academic System | time: 20 minutes | handoff: "
- Missed step: "Notify Approval | tools: Email | time: 10 minutes | handoff: "
- Exception: "Incorrect ticket information | Delays in processin" ↔ "Missing or wrong information provided by the stude" (sim=0.835681)

### Process alignment (truth[2] ↔ recon[2], aggregate=0.652733)
- Step: "Closed | tools: Incident Management System | time: 5 minutes" ↔ "Monitor status of open incidents | tools: Incident Managemen" (sim=0.800904)
- Step: "Assignment | tools: Incident Management System | time: 15 mi" ↔ "Coordinate incidents by forwarding cases and checking pendin" (sim=0.754848)
- Missed step: "Open | tools: Incident Management System | time: 10 minutes | handoff: Assignmen"
- Missed step: "Operator Update | tools: Communication Platform | time: 30 minutes | handoff: Qu"
- Missed step: "Status Change | tools: Incident Management System | time: 10 minutes | handoff: "
- Exception: "Status not updated correctly | Miscommunication on" ↔ "Incident status not updated correctly in the Incid" (sim=0.82878)

### Process alignment (truth[1] ↔ recon[1], aggregate=0.618006)
- Step: "Inform Complainant | tools: Email | time: 10 minutes | hando" ↔ "Communicate with complainants as needed | tools: email, inte" (sim=0.753375)
- Step: "New Complaint Received | tools: Complaint System | time: 15 " ↔ "Monitor status of open complaints | tools: Complaint System " (sim=0.747237)
- Step: "Forward Complaint Internally | tools: Internal Communication" ↔ "Coordinate complaints by forwarding cases and checking pendi" (sim=0.709277)
- Missed step: "Open a New Case | tools: Case Management Software | time: 30 minutes | handoff: "
- Missed step: "Receive References | tools: Reference Database | time: 1 hour | handoff: Verific"
- Missed step: "Confirm External Reference | tools: Verification System | time: 45 minutes | han"
- Exception: "Missing reference documents | Verification delays " ↔ "Missing reference documents in the complaint manag" (sim=0.798312)

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 2 | Most ground-truth steps are missing; multi-step workflows (6, 6, and 5 steps) are reduced to 3, 3, and 2 generic actions, omitting key actions like opening tickets/cases, notifications, system entries, verifications, and closure. The reconstruction captures only broad monitoring/forwarding themes. |
| Control Flow And Handoff Fidelity | 2 | The sequence is collapsed into generic monitoring/coordination, losing the specific handoff chain (e.g., CRA to Coordinator, Verification to Record Keeper, Closure team). Handoffs are often null or vague ('right teams'), and terminal steps are not preserved. |
| Attribute Accuracy | 2 | Durations are replaced by broad ranges or left blank, and several specific tools ('Academic System', 'Case Management Software', 'Reference Database', 'Verification System') are omitted while unspecific tools are added. Handoff targets are not faithful, frequently missing or generic instead of the named teams in the ground truth. |
| Exception And Edge Case Capture | 4 | All three exception themes are present with correct what-goes-wrong and recovery actions, semantically aligning with the ground truth. Added timing estimates slightly extend but do not contradict the core exceptions. |
| Faithfulness No Hallucination | 2 | The reconstruction introduces generic steps ('Monitor status', 'Coordinate incidents') and tools ('internal communication tools') and vague recipients ('right teams') not present in the ground truth. These additions reflect hallucinated generalizations rather than faithful extraction. |

---

*Embedding similarity uses greedy alignment by cosine similarity on field text. Judge scores are from a separate LLM comparison.*
