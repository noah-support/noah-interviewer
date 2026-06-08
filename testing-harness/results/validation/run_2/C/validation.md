# Validation report — run_2 / persona C

Generated: 2026-06-07 18:17 UTC

**Run:** `run_2`
**Input:** `results/run_2`
**Output:** `results/validation/run_2`

Ground truth: `persona.json` (backstory ignored for scoring).

## Noah

Reconstruction: `result_noah.json`

**Overall embedding similarity:** 0.900001
**Unmatched counts:** processes missed=0, extra=0; steps missed=0, extra=1; exceptions missed=0, extra=0

### Process alignment (truth[1] ↔ recon[1], aggregate=0.897098)
- Step: "Update Ticket | tools: Ticketing System | time: 20 minutes |" ↔ "Update the ticket | tools: ticketing system | time: 20 minut" (sim=0.953475)
- Step: "Open Ticket | tools: Ticketing System | time: 10 minutes | h" ↔ "Open a ticket | tools: ticketing system | time: 10 minutes |" (sim=0.931753)
- Step: "Closed | tools: Ticketing System | time: 5 minutes | handoff" ↔ "Close the ticket | tools: ticketing system | time: 5 minutes" (sim=0.91175)
- Step: "Status Change | tools: Status Management Software | time: 10" ↔ "Change ticket status | tools: status management software | t" (sim=0.86074)
- Step: "Assignment | tools: Assignment Tool | time: 15 minutes | han" ↔ "Assign the ticket | tools: assignment tool | time: 15 minute" (sim=0.858168)
- Exception: "Ticket not assigned correctly | Prolonged resoluti" ↔ "Ticket not being assigned correctly | Prolongs res" (sim=0.961981)

### Process alignment (truth[2] ↔ recon[2], aggregate=0.910196)
- Step: "Project Arrival | tools: Project Management Software | time:" ↔ "Project arrival | tools: project management software | time:" (sim=0.98561)
- Step: "Visit in Loco | tools: Field Tools | time: 3 hours | handoff" ↔ "Visit in loco | tools: field tools | time: 3 hours | handoff" (sim=0.961725)
- Step: "Evaluate Project | tools: Evaluation Tools | time: 2 hours |" ↔ "Evaluate the project | tools: evaluation tools | time: 2 hou" (sim=0.954532)
- Step: "Register Project | tools: Database Software | time: 30 minut" ↔ "Register the project | tools: database software | time: 30 m" (sim=0.934326)
- Step: "Fill Report | tools: Reporting Software | time: 1 hour | han" ↔ "Fill out reports | tools: reporting software | time: 1 hour " (sim=0.929688)
- Exception: "Incorrect project data entry | Incorrect evaluatio" ↔ "Incorrect project data entry | Delays project prog" (sim=0.84953)

### Process alignment (truth[0] ↔ recon[0], aggregate=0.955119)
- Step: "Schedule Scuba Diving | tools: Diving Scheduling Software | " ↔ "Schedule scuba diving | tools: diving scheduling software | " (sim=0.991308)
- Step: "Inform Reservation Data | tools: Reservation System | time: " ↔ "Inform reservation data | tools: reservation system | time: " (sim=0.98353)
- Step: "Choose Accommodations | tools: Booking Platform | time: 1 ho" ↔ "Choose accommodations | tools: booking platform | time: 1 ho" (sim=0.978557)
- Step: "Book Diving Equipment | tools: Equipment Booking Tool | time" ↔ "Book diving equipment | tools: equipment booking tool | time" (sim=0.964755)
- Extra step: "Billing process | tools:  | time:  | handoff: "
- Exception: "Reservation data is incomplete | Delays in booking" ↔ "Incomplete reservation data | Delays booking accom" (sim=0.908527)

### Process alignment (truth[3] ↔ recon[3], aggregate=0.884388)
- Step: "Casting | tools: Casting Tools | time: 2 hours | handoff: Cu" ↔ "Handle the casting process | tools: casting tools | time: 2 " (sim=0.942986)
- Step: "Project Evaluation | tools: Evaluation Software | time: 1 ho" ↔ "Conduct project evaluation | tools: evaluation software | ti" (sim=0.930242)
- Step: "Finishing | tools: Finishing Tools | time: 2 hours | handoff" ↔ "Complete the process | tools: finishing tools | time: 2 hour" (sim=0.921798)
- Step: "Cutting | tools: Cutting Equipment | time: 1 hour | handoff:" ↔ "Manage the cutting process | tools: cutting equipment | time" (sim=0.915989)
- Step: "Forward Project to Production | tools: Production Scheduling" ↔ "Forward project to Casting Coordinator | tools: production s" (sim=0.889384)
- Step: "New Order | tools: Order Management System | time: 20 minute" ↔ "Handle a new order | tools: order management system | time: " (sim=0.883336)
- Exception: "Production delay due to equipment failure | Delaye" ↔ "Production delays due to equipment failure | Delay" (sim=0.979667)

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 5 | All original steps from each of the four processes are present in the reconstruction with no omissions. Core sequencing is preserved for the matched steps. |
| Control Flow And Handoff Fidelity | 4 | Handoffs and overall sequence largely match the ground truth, but an extra 'Billing process' step with null handoff slightly distorts the vacation process flow. Otherwise, handoff targets and order remain consistent. |
| Attribute Accuracy | 5 | For the matched steps, tools, times, and handoff targets align closely with the ground truth; wording differences do not change meaning. No discrepancies found in micro-details for the core steps. |
| Exception And Edge Case Capture | 4 | All processes include the expected exception entries; three match closely, while the construction process alters the impact to a generic delay instead of an incorrect evaluation outcome. |
| Faithfulness No Hallucination | 4 | The reconstruction is mostly faithful but introduces a hallucinated 'Billing process' step in the vacation workflow. Other variations are rephrasings rather than inventions. |

## ElevenLabs

Reconstruction: `result_elevenlabs.json`

**Overall embedding similarity:** 0.555622
**Unmatched counts:** processes missed=0, extra=2; steps missed=17, extra=0; exceptions missed=0, extra=0

### Process alignment (truth[0] ↔ recon[2], aggregate=0.922824)
- Missed step: "Inform Reservation Data | tools: Reservation System | time: 30 minutes | handoff"
- Missed step: "Choose Accommodations | tools: Booking Platform | time: 1 hour | handoff: Billin"
- Missed step: "Schedule Scuba Diving | tools: Diving Scheduling Software | time: 45 minutes | h"
- Missed step: "Book Diving Equipment | tools: Equipment Booking Tool | time: 30 minutes | hando"
- Exception: "Reservation data is incomplete | Delays in booking" ↔ "Reservation data is incomplete | Delays in booking" (sim=0.900442)

### Process alignment (truth[1] ↔ recon[3], aggregate=0.787096)
- Missed step: "Open Ticket | tools: Ticketing System | time: 10 minutes | handoff: Update Speci"
- Missed step: "Update Ticket | tools: Ticketing System | time: 20 minutes | handoff: Assignment"
- Missed step: "Assignment | tools: Assignment Tool | time: 15 minutes | handoff: Status Manager"
- Missed step: "Status Change | tools: Status Management Software | time: 10 minutes | handoff: "
- Missed step: "Closed | tools: Ticketing System | time: 5 minutes | handoff: "
- Exception: "Ticket not assigned correctly | Prolonged resoluti" ↔ "Incorrect ticket assignments | Extends resolution " (sim=0.790457)

### Process alignment (truth[2] ↔ recon[4], aggregate=0.613531)
- Step: "Visit in Loco | tools: Field Tools | time: 3 hours | handoff" ↔ "Manual data entry and verification | tools:  | time: around " (sim=0.630683)
- Missed step: "Project Arrival | tools: Project Management Software | time: 1 hour | handoff: R"
- Missed step: "Register Project | tools: Database Software | time: 30 minutes | handoff: Evalua"
- Missed step: "Evaluate Project | tools: Evaluation Tools | time: 2 hours | handoff: Report Fil"
- Missed step: "Fill Report | tools: Reporting Software | time: 1 hour | handoff: Permit Issuer"
- Exception: "Incorrect project data entry | Incorrect evaluatio" ↔ "The manual process is error-prone; incorrect infor" (sim=0.733761)

### Process alignment (truth[3] ↔ recon[5], aggregate=0.30034)
- Step: "Project Evaluation | tools: Evaluation Software | time: 1 ho" ↔ "Reporting and documentation | tools:  | time: around 5 hours" (sim=0.617348)
- Step: "Finishing | tools: Finishing Tools | time: 2 hours | handoff" ↔ "Follow-up activities checking progress of implemented change" (sim=0.53797)
- Missed step: "New Order | tools: Order Management System | time: 20 minutes | handoff: Project"
- Missed step: "Forward Project to Production | tools: Production Scheduling Software | time: 30"
- Missed step: "Casting | tools: Casting Tools | time: 2 hours | handoff: Cutting Supervisor"
- Missed step: "Cutting | tools: Cutting Equipment | time: 1 hour | handoff: Finishing Specialis"
- Exception: "Production delay due to equipment failure | Delaye" ↔ "Hard to track the long-term performance of process" (sim=0.278075)
- Extra process: "Analyzing workflows"
- Extra process: "Implementing strategies to fix bottlenecks"

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 1 | Most ground-truth steps are missing, with no steps for Vacation Planning or Ticket Management, only one generic step for Construction, and the entire Manufacturing process omitted. |
| Control Flow And Handoff Fidelity | 1 | The logical sequences and handoffs are not preserved since steps are largely absent and handoff targets are mostly null or unspecified. |
| Attribute Accuracy | 1 | For the few steps provided, tools, durations, and handoffs do not match the ground truth (e.g., vague weekly times, missing tools, and null handoffs). |
| Exception And Edge Case Capture | 3 | Three of the four ground-truth exceptions are captured with close semantics, but the Manufacturing exception is missing and some impacts are altered. |
| Faithfulness No Hallucination | 1 | Several invented processes and exceptions are introduced (e.g., analyzing workflows, reporting/follow-up), which are not present in the ground truth. |

---

*Embedding similarity uses greedy alignment by cosine similarity on field text. Judge scores are from a separate LLM comparison.*
