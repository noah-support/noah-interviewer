# Validation report — persona C

Generated: 2026-06-05 15:59 UTC

Ground truth: `persona.json` (backstory ignored for scoring).

## Noah

Reconstruction: `result_noah.json`

**Overall embedding similarity:** 0.176421
**Unmatched counts:** processes missed=0, extra=1; steps missed=11, extra=0; exceptions missed=0, extra=2

### Process alignment (truth[2] ↔ recon[1], aggregate=0.128405)
- Step: "Project Arrival | tools: Project Management Software | time:" ↔ "Send out invitations to relevant stakeholders | tools:  | ti" (sim=0.554937)
- Step: "Evaluate Project | tools: Evaluation Tools | time: 2 hours |" ↔ "Prepare an agenda outlining key topics | tools:  | time:  | " (sim=0.554398)
- Step: "Visit in Loco | tools: Field Tools | time: 3 hours | handoff" ↔ "Take notes and summarize key action items at the end | tools" (sim=0.506335)
- Step: "Register Project | tools: Database Software | time: 30 minut" ↔ "Follow up with a summary email and any next steps | tools:  " (sim=0.471817)
- Step: "Fill Report | tools: Reporting Software | time: 1 hour | han" ↔ "Facilitate the discussion to ensure everyone's input is hear" (sim=0.415733)
- Exception: "Incorrect project data entry | Incorrect evaluatio" ↔ "Not all stakeholders are present. | Hinders decisi" (sim=0.318893)
- Extra exception: "Discussions can go off-topic or participants might have differing opinions that "

### Process alignment (truth[1] ↔ recon[3], aggregate=0.261706)
- Step: "Closed | tools: Ticketing System | time: 5 minutes | handoff" ↔ "Identify the root cause of the issue | tools:  | time:  | ha" (sim=0.551807)
- Missed step: "Open Ticket | tools: Ticketing System | time: 10 minutes | handoff: Update Speci"
- Missed step: "Update Ticket | tools: Ticketing System | time: 20 minutes | handoff: Assignment"
- Missed step: "Assignment | tools: Assignment Tool | time: 15 minutes | handoff: Status Manager"
- Missed step: "Status Change | tools: Status Management Software | time: 10 minutes | handoff: "
- Exception: "Ticket not assigned correctly | Prolonged resoluti" ↔ "The issue might be more complex than initially tho" (sim=0.456875)

### Process alignment (truth[3] ↔ recon[0], aggregate=0.168052)
- Step: "Project Evaluation | tools: Evaluation Software | time: 1 ho" ↔ "Set up a meeting with the relevant department | tools:  | ti" (sim=0.536581)
- Missed step: "New Order | tools: Order Management System | time: 20 minutes | handoff: Project"
- Missed step: "Forward Project to Production | tools: Production Scheduling Software | time: 30"
- Missed step: "Casting | tools: Casting Tools | time: 2 hours | handoff: Cutting Supervisor"
- Missed step: "Cutting | tools: Cutting Equipment | time: 1 hour | handoff: Finishing Specialis"
- Missed step: "Finishing | tools: Finishing Tools | time: 2 hours | handoff: "
- Exception: "Production delay due to equipment failure | Delaye" ↔ "Miscommunication or lack of clarity about process " (sim=0.434642)

### Process alignment (truth[0] ↔ recon[2], aggregate=0.197849)
- Step: "Choose Accommodations | tools: Booking Platform | time: 1 ho" ↔ "Review the tool or method's documentation to understand its " (sim=0.484362)
- Step: "Book Diving Equipment | tools: Equipment Booking Tool | time" ↔ "Identify integration issues and assess if the tool meets req" (sim=0.458283)
- Missed step: "Inform Reservation Data | tools: Reservation System | time: 30 minutes | handoff"
- Missed step: "Schedule Scuba Diving | tools: Diving Scheduling Software | time: 45 minutes | h"
- Exception: "Reservation data is incomplete | Delays in booking" ↔ "Unforeseen technical issues or a steeper learning " (sim=0.256656)
- Extra exception: "The tool or method does not address our specific needs. | Wastes time and resour"
- Extra process: "training staff on new processes or tools"

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 1 | The reconstructed profile lacks all original steps and introduces entirely new processes not present in the ground truth. |
| Control Flow And Handoff Fidelity | 1 | The sequence and handoff chains are incorrect as they do not match any of the ground truth processes. |
| Attribute Accuracy | 1 | Attributes such as tools, time needed, and handoff details are missing or incorrect compared to the ground truth. |
| Exception And Edge Case Capture | 1 | The exceptions captured in the reconstructed profile do not align with those in the ground truth. |
| Faithfulness No Hallucination | 1 | The reconstructed profile introduces processes and steps that are not present in the ground truth, indicating hallucination. |

## ElevenLabs

Reconstruction: `result_elevenlabs.json`

**Overall embedding similarity:** 0.322058
**Unmatched counts:** processes missed=0, extra=0; steps missed=8, extra=0; exceptions missed=0, extra=0

### Process alignment (truth[1] ↔ recon[1], aggregate=0.390048)
- Step: "Closed | tools: Ticketing System | time: 5 minutes | handoff" ↔ "data gathering | tools: Ticketing Systems | time:  | handoff" (sim=0.779807)
- Step: "Open Ticket | tools: Ticketing System | time: 10 minutes | h" ↔ "workflow mapping | tools: Ticketing Systems | time:  | hando" (sim=0.674188)
- Step: "Assignment | tools: Assignment Tool | time: 15 minutes | han" ↔ "implement improvements | tools:  | time:  | handoff: " (sim=0.549219)
- Missed step: "Update Ticket | tools: Ticketing System | time: 20 minutes | handoff: Assignment"
- Missed step: "Status Change | tools: Status Management Software | time: 10 minutes | handoff: "
- Exception: "Ticket not assigned correctly | Prolonged resoluti" ↔ "Incorrect ticket assignments | Prolongs resolution" (sim=0.818675)

### Process alignment (truth[2] ↔ recon[2], aggregate=0.306909)
- Step: "Project Arrival | tools: Project Management Software | time:" ↔ "data gathering | tools: Project Management Software | time: " (sim=0.737924)
- Step: "Evaluate Project | tools: Evaluation Tools | time: 2 hours |" ↔ "implement improvements | tools:  | time:  | handoff: " (sim=0.593613)
- Step: "Register Project | tools: Database Software | time: 30 minut" ↔ "workflow mapping | tools: Project Management Software | time" (sim=0.563127)
- Missed step: "Fill Report | tools: Reporting Software | time: 1 hour | handoff: Permit Issuer"
- Missed step: "Visit in Loco | tools: Field Tools | time: 3 hours | handoff: "
- Exception: "Incorrect project data entry | Incorrect evaluatio" ↔ "Incorrect project data entry | Affects evaluations" (sim=0.830224)

### Process alignment (truth[3] ↔ recon[3], aggregate=0.248867)
- Step: "Project Evaluation | tools: Evaluation Software | time: 1 ho" ↔ "data gathering | tools:  | time:  | handoff: " (sim=0.635598)
- Step: "Finishing | tools: Finishing Tools | time: 2 hours | handoff" ↔ "implement improvements | tools:  | time:  | handoff: " (sim=0.63386)
- Step: "New Order | tools: Order Management System | time: 20 minute" ↔ "workflow mapping | tools:  | time:  | handoff: " (sim=0.572576)
- Missed step: "Forward Project to Production | tools: Production Scheduling Software | time: 30"
- Missed step: "Casting | tools: Casting Tools | time: 2 hours | handoff: Cutting Supervisor"
- Missed step: "Cutting | tools: Cutting Equipment | time: 1 hour | handoff: Finishing Specialis"
- Exception: "Production delay due to equipment failure | Delaye" ↔ "Equipment failures | Causes production delays | " (sim=0.675743)

### Process alignment (truth[0] ↔ recon[0], aggregate=0.396245)
- Step: "Inform Reservation Data | tools: Reservation System | time: " ↔ "data gathering | tools: Reservation Systems | time:  | hando" (sim=0.74943)
- Step: "Choose Accommodations | tools: Booking Platform | time: 1 ho" ↔ "workflow mapping | tools: Reservation Systems | time:  | han" (sim=0.631611)
- Step: "Book Diving Equipment | tools: Equipment Booking Tool | time" ↔ "implement improvements | tools:  | time:  | handoff: " (sim=0.511402)
- Missed step: "Schedule Scuba Diving | tools: Diving Scheduling Software | time: 45 minutes | h"
- Exception: "Reservation data is incomplete | Delays in booking" ↔ "Incomplete reservation data | Delays bookings | Co" (sim=0.844935)

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 1 | The reconstructed processes lack many original steps and introduce generic steps not present in the ground truth. |
| Control Flow And Handoff Fidelity | 1 | The sequence and handoff details are missing or incorrect, with no specific handoffs captured. |
| Attribute Accuracy | 1 | Attributes such as tools, time_needed, and handoff_to are largely missing or incorrect. |
| Exception And Edge Case Capture | 3 | Exceptions are partially captured but lack complete recovery details. |
| Faithfulness No Hallucination | 2 | The reconstructed profile includes generic steps like 'data gathering' and 'workflow mapping' not present in the ground truth. |

---

*Embedding similarity uses greedy alignment by cosine similarity on field text. Judge scores are from a separate LLM comparison.*
