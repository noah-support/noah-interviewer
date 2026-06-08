# Validation report — run_1 / persona C

Generated: 2026-06-07 17:55 UTC

**Run:** `run_1`
**Input:** `results/run_1`
**Output:** `results/validation/run_1`

Ground truth: `persona.json` (backstory ignored for scoring).

## Noah

Reconstruction: `result_noah.json`

**Overall embedding similarity:** 0.157641
**Unmatched counts:** processes missed=0, extra=1; steps missed=6, extra=3; exceptions missed=0, extra=3

### Process alignment (truth[2] ↔ recon[1], aggregate=0.128888)
- Step: "Evaluate Project | tools: Evaluation Tools | time: 2 hours |" ↔ "Take notes and summarize key action items at the end | tools" (sim=0.567636)
- Step: "Project Arrival | tools: Project Management Software | time:" ↔ "Send out invitations to relevant stakeholders with necessary" (sim=0.56087)
- Step: "Visit in Loco | tools: Field Tools | time: 3 hours | handoff" ↔ "Prepare an agenda outlining key topics | tools:  | time:  | " (sim=0.535213)
- Step: "Fill Report | tools: Reporting Software | time: 1 hour | han" ↔ "Follow up with a summary email and any next steps | tools:  " (sim=0.479567)
- Step: "Register Project | tools: Database Software | time: 30 minut" ↔ "Focus on identifying pain points and brainstorming potential" (sim=0.431254)
- Extra step: "Start the meeting by going over the agenda | tools:  | time:  | handoff: "
- Extra step: "Facilitate the discussion to ensure everyone's input is heard | tools:  | time: "
- Exception: "Incorrect project data entry | Incorrect evaluatio" ↔ "Not all stakeholders are present. | Hinders decisi" (sim=0.320258)
- Extra exception: "Discussions can go off-topic or participants might have differing opinions that "

### Process alignment (truth[1] ↔ recon[3], aggregate=0.166512)
- Step: "Open Ticket | tools: Ticketing System | time: 10 minutes | h" ↔ "Determine the best course of action to resolve it (e.g., con" (sim=0.641821)
- Step: "Closed | tools: Ticketing System | time: 5 minutes | handoff" ↔ "Identify the root cause of the issue | tools:  | time:  | ha" (sim=0.571608)
- Step: "Assignment | tools: Assignment Tool | time: 15 minutes | han" ↔ "Assess the impact on the overall process | tools:  | time:  " (sim=0.556926)
- Missed step: "Update Ticket | tools: Ticketing System | time: 20 minutes | handoff: Assignment"
- Missed step: "Status Change | tools: Status Management Software | time: 10 minutes | handoff: "
- Exception: "Ticket not assigned correctly | Prolonged resoluti" ↔ "The issue might be more complex than initially tho" (sim=0.474311)

### Process alignment (truth[3] ↔ recon[0], aggregate=0.204958)
- Step: "Project Evaluation | tools: Evaluation Software | time: 1 ho" ↔ "Understand their current processes and identify any challeng" (sim=0.552827)
- Step: "Finishing | tools: Finishing Tools | time: 2 hours | handoff" ↔ "Set up a meeting with the relevant department | tools:  | ti" (sim=0.54234)
- Missed step: "New Order | tools: Order Management System | time: 20 minutes | handoff: Project"
- Missed step: "Forward Project to Production | tools: Production Scheduling Software | time: 30"
- Missed step: "Casting | tools: Casting Tools | time: 2 hours | handoff: Cutting Supervisor"
- Missed step: "Cutting | tools: Cutting Equipment | time: 1 hour | handoff: Finishing Specialis"
- Exception: "Production delay due to equipment failure | Delaye" ↔ "Conflicting priorities between departments | Delay" (sim=0.444694)
- Extra exception: "Miscommunication or lack of clarity about process requirements | Delays progress"

### Process alignment (truth[0] ↔ recon[2], aggregate=0.136545)
- Step: "Book Diving Equipment | tools: Equipment Booking Tool | time" ↔ "Identify integration issues and assess if the tool meets req" (sim=0.497798)
- Step: "Schedule Scuba Diving | tools: Diving Scheduling Software | " ↔ "Consider ease of use and the level of training required for " (sim=0.462325)
- Step: "Choose Accommodations | tools: Booking Platform | time: 1 ho" ↔ "Review the tool or method's documentation to understand its " (sim=0.460711)
- Step: "Inform Reservation Data | tools: Reservation System | time: " ↔ "Evaluate whether it can be implemented without disrupting cu" (sim=0.420134)
- Extra step: "Assess whether the tool or method addresses specific needs | tools:  | time:  | "
- Exception: "Reservation data is incomplete | Delays in booking" ↔ "Unforeseen technical issues or a steeper learning " (sim=0.256656)
- Extra exception: "The tool or method does not address our specific needs. | Wastes time and resour"
- Extra process: "training staff on new processes or tools"

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 1 | None of the ground-truth processes or their steps are present; the reconstruction replaces them with unrelated, generic workflows. |
| Control Flow And Handoff Fidelity | 1 | The ground truth has ordered steps with explicit handoffs, while the reconstruction offers generic sequences with no meaningful handoffs, so the structural flow does not align. |
| Attribute Accuracy | 1 | Tools, time estimates, and handoff targets from the ground truth are missing or empty, and step names don’t correspond, resulting in inaccurate or absent attributes. |
| Exception And Edge Case Capture | 2 | Ground-truth exceptions are specific per process with clear recoveries; the reconstruction lists generic issues and only loosely echoes two themes (missing info, ticket reassignment) without proper alignment. |
| Faithfulness No Hallucination | 1 | The reconstruction invents five generic processes and multiple steps not in the ground truth while omitting all expected content, indicating substantial hallucination. |

## ElevenLabs

Reconstruction: `result_elevenlabs.json`

**Overall embedding similarity:** 0.222688
**Unmatched counts:** processes missed=0, extra=0; steps missed=0, extra=8; exceptions missed=0, extra=0

### Process alignment (truth[1] ↔ recon[1], aggregate=0.254763)
- Step: "Closed | tools: Ticketing System | time: 5 minutes | handoff" ↔ "Troubleshoot issues | tools:  | time:  | handoff: " (sim=0.658374)
- Step: "Open Ticket | tools: Ticketing System | time: 10 minutes | h" ↔ "Gather data on the current process | tools: Project Manageme" (sim=0.599555)
- Step: "Assignment | tools: Assignment Tool | time: 15 minutes | han" ↔ "Implement successful strategies | tools:  | time:  | handoff" (sim=0.571053)
- Step: "Update Ticket | tools: Ticketing System | time: 20 minutes |" ↔ "Map out each step and identify bottlenecks | tools: Project " (sim=0.568045)
- Step: "Status Change | tools: Status Management Software | time: 10" ↔ "Monitor impact over time | tools:  | time:  | handoff: " (sim=0.501777)
- Extra step: "Brainstorm potential improvements | tools:  | time:  | handoff: "
- Extra step: "Test changes in a controlled environment | tools:  | time:  | handoff: "
- Exception: "Ticket not assigned correctly | Prolonged resoluti" ↔ "Incorrect ticket assignments | Prolongs resolution" (sim=0.807795)

### Process alignment (truth[2] ↔ recon[2], aggregate=0.227773)
- Step: "Project Arrival | tools: Project Management Software | time:" ↔ "Gather data on the current process | tools: Project Manageme" (sim=0.645324)
- Step: "Evaluate Project | tools: Evaluation Tools | time: 2 hours |" ↔ "Implement successful strategies | tools:  | time:  | handoff" (sim=0.593835)
- Step: "Visit in Loco | tools: Field Tools | time: 3 hours | handoff" ↔ "Troubleshoot issues | tools:  | time:  | handoff: " (sim=0.584084)
- Step: "Fill Report | tools: Reporting Software | time: 1 hour | han" ↔ "Monitor impact over time | tools:  | time:  | handoff: " (sim=0.492016)
- Step: "Register Project | tools: Database Software | time: 30 minut" ↔ "Test changes in a controlled environment | tools:  | time:  " (sim=0.487179)
- Extra step: "Map out each step and identify bottlenecks | tools: Project Management Software,"
- Extra step: "Brainstorm potential improvements | tools:  | time:  | handoff: "
- Exception: "Incorrect project data entry | Incorrect evaluatio" ↔ "Incorrect project data entry | Affects evaluations" (sim=0.836901)

### Process alignment (truth[3] ↔ recon[3], aggregate=0.186022)
- Step: "Project Evaluation | tools: Evaluation Software | time: 1 ho" ↔ "Gather data on the current process | tools: Project Manageme" (sim=0.599602)
- Step: "Finishing | tools: Finishing Tools | time: 2 hours | handoff" ↔ "Implement successful strategies | tools:  | time:  | handoff" (sim=0.572316)
- Step: "Forward Project to Production | tools: Production Scheduling" ↔ "Map out each step and identify bottlenecks | tools: Project " (sim=0.565854)
- Step: "New Order | tools: Order Management System | time: 20 minute" ↔ "Troubleshoot issues | tools:  | time:  | handoff: " (sim=0.501523)
- Step: "Casting | tools: Casting Tools | time: 2 hours | handoff: Cu" ↔ "Test changes in a controlled environment | tools:  | time:  " (sim=0.4729)
- Step: "Cutting | tools: Cutting Equipment | time: 1 hour | handoff:" ↔ "Monitor impact over time | tools:  | time:  | handoff: " (sim=0.454959)
- Extra step: "Brainstorm potential improvements | tools:  | time:  | handoff: "
- Exception: "Production delay due to equipment failure | Delaye" ↔ "Equipment failures | Cause production delays. | " (sim=0.691831)

### Process alignment (truth[0] ↔ recon[0], aggregate=0.282129)
- Step: "Inform Reservation Data | tools: Reservation System | time: " ↔ "Gather data on the current process | tools: Project Manageme" (sim=0.583828)
- Step: "Choose Accommodations | tools: Booking Platform | time: 1 ho" ↔ "Map out each step and identify bottlenecks | tools: Project " (sim=0.567971)
- Step: "Book Diving Equipment | tools: Equipment Booking Tool | time" ↔ "Troubleshoot issues | tools:  | time:  | handoff: " (sim=0.499706)
- Step: "Schedule Scuba Diving | tools: Diving Scheduling Software | " ↔ "Implement successful strategies | tools:  | time:  | handoff" (sim=0.451114)
- Extra step: "Brainstorm potential improvements | tools:  | time:  | handoff: "
- Extra step: "Test changes in a controlled environment | tools:  | time:  | handoff: "
- Extra step: "Monitor impact over time | tools:  | time:  | handoff: "
- Exception: "Reservation data is incomplete | Delays in booking" ↔ "Incomplete reservation data | Delays bookings; hap" (sim=0.705741)

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 2 | All four process areas are named, but the specific operational steps are replaced by generic improvement phases, omitting key activities like choosing accommodations, assignment, casting, and others. This results in major step omissions across all processes. |
| Control Flow And Handoff Fidelity | 1 | The reconstructed flows do not mirror the ground-truth sequences and omit all handoffs, presenting an analyze–implement cycle instead of the specified ordered steps. Consequently, the chain of handoffs is lost. |
| Attribute Accuracy | 1 | Micro-attributes are largely missing or incorrect: times are blank, handoffs are null, and tools are misapplied (e.g., project/ticketing tools listed for vacation steps). This diverges from the specified systems like Booking Platform, Assignment Tool, and Casting Tools. |
| Exception And Edge Case Capture | 3 | Unhappy paths are captured for all four processes with mostly correct high-level problems and impacts. However, recoveries are vague or missing for construction and manufacturing, and the ticketing recovery does not match the ground truth action. |
| Faithfulness No Hallucination | 2 | The reconstruction hallucinates numerous generic improvement steps and tool usages not present in the ground truth. While exception themes align, the added improvement-cycle content reduces precision. |

---

*Embedding similarity uses greedy alignment by cosine similarity on field text. Judge scores are from a separate LLM comparison.*
