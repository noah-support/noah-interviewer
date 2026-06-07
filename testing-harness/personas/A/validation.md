# Validation report — persona A

Generated: 2026-06-05 15:57 UTC

Ground truth: `persona.json` (backstory ignored for scoring).

## Noah

Reconstruction: `result_noah.json`

**Overall embedding similarity:** 0.589635
**Unmatched counts:** processes missed=0, extra=0; steps missed=1, extra=1; exceptions missed=0, extra=2

### Process alignment (truth[0] ↔ recon[0], aggregate=0.775488)
- Step: "Forward Process for Checking Pending Issues | tools: Sipac |" ↔ "Forward for checking pending issues | tools: Sipac | time: 2" (sim=0.933108)
- Step: "Enter in Academic System | tools: Academic System | time: 20" ↔ "Enter details into the Academic System | tools: Academic Sys" (sim=0.930901)
- Step: "Notify Student About Pending Issues | tools: Email | time: 1" ↔ "Notify the student about any pending matters | tools: email " (sim=0.898017)
- Step: "Student Opens Ticket | tools: Sipac | time: 15 minutes | han" ↔ "Open a ticket | tools: Sipac | time: 15 minutes | handoff: C" (sim=0.853293)
- Step: "Notify Approval | tools: Email | time: 10 minutes | handoff:" ↔ "Notify the Approval Team via email | tools: email | time:  |" (sim=0.815854)
- Step: "CRA Opens Process in Sipac | tools: Sipac | time: 30 minutes" ↔ "Update the ticket in Sipac | tools: Sipac | time:  | handoff" (sim=0.561016)
- Extra step: "Recover the ticket after resubmission | tools: ticketing system | time:  | hando"
- Exception: "Incorrect ticket information | Delays in processin" ↔ "Incorrect ticket information | Delays processing |" (sim=0.985357)
- Extra exception: "Delay in receiving correct information | Slows down the entire process and affec"

### Process alignment (truth[1] ↔ recon[1], aggregate=0.53136)
- Step: "Forward Complaint Internally | tools: Internal Communication" ↔ "Forward the complaint internally | tools: internal communica" (sim=0.907051)
- Step: "New Complaint Received | tools: Complaint System | time: 15 " ↔ "Receive a new complaint in the Complaint System | tools: Com" (sim=0.880082)
- Step: "Inform Complainant | tools: Email | time: 10 minutes | hando" ↔ "Inform the complainant via email | tools: email | time:  | h" (sim=0.847665)
- Step: "Open a New Case | tools: Case Management Software | time: 30" ↔ "Open a case in the case management software | tools:  | time" (sim=0.828005)
- Step: "Confirm External Reference | tools: Verification System | ti" ↔ "Update the records after confirming the external reference |" (sim=0.724051)
- Step: "Receive References | tools: Reference Database | time: 1 hou" ↔ "Obtain missing documents | tools:  | time:  | handoff: exter" (sim=0.623687)
- Exception: "Missing reference documents | Verification delays " ↔ "Missing reference documents | Causes verification " (sim=0.957849)
- Extra exception: "Delays due to missing reference documents | Slows down the entire process until "

### Process alignment (truth[2] ↔ recon[2], aggregate=0.466435)
- Step: "Closed | tools: Incident Management System | time: 5 minutes" ↔ "Close the incident | tools:  | time:  | handoff: " (sim=0.829608)
- Step: "Assignment | tools: Incident Management System | time: 15 mi" ↔ "Open an incident in the Incident Management System | tools: " (sim=0.823711)
- Step: "Operator Update | tools: Communication Platform | time: 30 m" ↔ "Update the status | tools:  | time:  | handoff: quality assu" (sim=0.732697)
- Step: "Open | tools: Incident Management System | time: 10 minutes " ↔ "Assign it to the resolution team | tools:  | time:  | handof" (sim=0.672412)
- Missed step: "Status Change | tools: Incident Management System | time: 10 minutes | handoff: "
- Exception: "Status not updated correctly | Miscommunication on" ↔ "Status might not be updated correctly | Leads to m" (sim=0.916977)

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 3 | The reconstructed profile includes most original steps but introduces new steps and omits some, such as 'CRA Opens Process in Sipac'. |
| Control Flow And Handoff Fidelity | 3 | The sequence of steps and handoffs is mostly correct, but some steps have incorrect or missing handoffs. |
| Attribute Accuracy | 2 | Several attributes such as 'time_needed' and 'handoff_to' are missing or incorrect in the reconstructed profile. |
| Exception And Edge Case Capture | 4 | The exceptions are mostly captured correctly, with some additional details provided in the reconstructed profile. |
| Faithfulness No Hallucination | 2 | The reconstructed profile introduces several steps and tools not present in the ground truth, such as 'Recover the ticket after resubmission'. |

## ElevenLabs

Reconstruction: `result_elevenlabs.json`

**Overall embedding similarity:** 0.603714
**Unmatched counts:** processes missed=0, extra=0; steps missed=13, extra=0; exceptions missed=1, extra=0

### Process alignment (truth[0] ↔ recon[0], aggregate=0.68946)
- Step: "Student Opens Ticket | tools: Sipac | time: 15 minutes | han" ↔ "Check new student tickets | tools: Sipac | time: 60 to 90 mi" (sim=0.766882)
- Step: "Notify Approval | tools: Email | time: 10 minutes | handoff:" ↔ "Coordinate with teams | tools: Email, internal communication" (sim=0.629177)
- Missed step: "CRA Opens Process in Sipac | tools: Sipac | time: 30 minutes | handoff: Coordina"
- Missed step: "Forward Process for Checking Pending Issues | tools: Sipac | time: 2 hours | han"
- Missed step: "Notify Student About Pending Issues | tools: Email | time: 10 minutes | handoff:"
- Missed step: "Enter in Academic System | tools: Academic System | time: 20 minutes | handoff: "
- Exception: "Incorrect ticket information | Delays in processin" ↔ "Incorrect ticket information | Delays by a few hou" (sim=0.926716)

### Process alignment (truth[2] ↔ recon[2], aggregate=0.578268)
- Step: "Closed | tools: Incident Management System | time: 5 minutes" ↔ "Handle incidents | tools: Incident Management System | time:" (sim=0.800668)
- Missed step: "Open | tools: Incident Management System | time: 10 minutes | handoff: Assignmen"
- Missed step: "Assignment | tools: Incident Management System | time: 15 minutes | handoff: Res"
- Missed step: "Operator Update | tools: Communication Platform | time: 30 minutes | handoff: Qu"
- Missed step: "Status Change | tools: Incident Management System | time: 10 minutes | handoff: "
- Exception: "Status not updated correctly | Miscommunication on" ↔ "Miscommunication about incident progress | Extra t" (sim=0.80518)

### Process alignment (truth[1] ↔ recon[1], aggregate=0.522146)
- Step: "New Complaint Received | tools: Complaint System | time: 15 " ↔ "Manage complaints | tools: Complaint System | time:  | hando" (sim=0.778727)
- Missed step: "Open a New Case | tools: Case Management Software | time: 30 minutes | handoff: "
- Missed step: "Forward Complaint Internally | tools: Internal Communication Tool | time: 20 min"
- Missed step: "Receive References | tools: Reference Database | time: 1 hour | handoff: Verific"
- Missed step: "Confirm External Reference | tools: Verification System | time: 45 minutes | han"
- Missed step: "Inform Complainant | tools: Email | time: 10 minutes | handoff: "
- Missed exception: "Missing reference documents | Verification delays | Contact external sources for"

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 1 | The reconstructed process omits many steps present in the ground truth and introduces new ones. |
| Control Flow And Handoff Fidelity | 1 | The sequence and handoffs are incorrect, with many steps missing and no clear handoff chain. |
| Attribute Accuracy | 2 | Some tools and exceptions are correctly identified, but time estimates and handoffs are often missing or incorrect. |
| Exception And Edge Case Capture | 3 | Exceptions are partially captured but lack detail and completeness compared to the ground truth. |
| Faithfulness No Hallucination | 2 | The reconstructed process includes steps and tools not present in the ground truth, indicating some hallucination. |

---

*Embedding similarity uses greedy alignment by cosine similarity on field text. Judge scores are from a separate LLM comparison.*
