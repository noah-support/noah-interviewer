# Validation report — run_2 / persona B

Generated: 2026-06-07 18:14 UTC

**Run:** `run_2`
**Input:** `results/run_2`
**Output:** `results/validation/run_2`

Ground truth: `persona.json` (backstory ignored for scoring).

## Noah

Reconstruction: `result_noah.json`

**Overall embedding similarity:** 0.400196
**Unmatched counts:** processes missed=0, extra=5; steps missed=2, extra=3; exceptions missed=0, extra=2

### Process alignment (truth[0] ↔ recon[0], aggregate=0.526069)
- Step: "Check_and_Repair_Hardware | tools: Hardware Diagnostic Tool " ↔ "Start hardware diagnostics | tools: Hardware Diagnostic Tool" (sim=0.801924)
- Step: "Test_System_Functionality | tools: System Testing Suite | ti" ↔ "Test system functionality after repairs | tools: System Test" (sim=0.800491)
- Step: "Return_Computer_Without_Repair | tools:  | time: 10 minutes " ↔ "Assess whether the computer can be repaired or should be ret" (sim=0.793994)
- Step: "Check_and_Configure_Software | tools: Software Configuration" ↔ "Check and configure software as needed | tools:  | time:  | " (sim=0.744861)
- Step: "Provide_Repair_Cost_Calculation | tools: Billing Software | " ↔ "Continue with the repair after diagnostics | tools:  | time:" (sim=0.595813)
- Extra step: "Order the needed hardware component if unavailable | tools: supplier's online or"
- Extra step: "Install the component and continue diagnostics | tools:  | time:  | handoff: "
- Extra step: "Return repaired computer to the customer | tools:  | time:  | handoff: customer"
- Exception: "Hardware component not available | Delays the repa" ↔ "Necessary hardware component isn't available | Del" (sim=0.947572)
- Extra exception: "Some configurations didn't take effect or new software problems emerged | System"
- Extra exception: "Billing software errors during the process | Leads to inaccurate estimates | Man"

### Process alignment (truth[1] ↔ recon[6], aggregate=0.26458)
- Step: "Return_Repaired_Computer | tools:  | time: 10 minutes | hand" ↔ "Return the computer to the customer | tools:  | time:  | han" (sim=0.732144)
- Step: "Return_Computer_Without_Repair | tools:  | time: 10 minutes " ↔ "Prepare the computer for return | tools:  | time:  | handoff" (sim=0.64294)
- Step: "Billing | tools: Billing Software | time: 20 minutes | hando" ↔ "Provide any necessary documentation | tools:  | time:  | han" (sim=0.557987)
- Step: "Check_and_Repair_Hardware | tools: Hardware Diagnostic Tool " ↔ "Discuss the situation with the customer to explain why it's " (sim=0.54859)
- Missed step: "Check_and_Configure_Software | tools: Software Configuration Utility | time: 1 h"
- Missed step: "Test_System_Functionality | tools: System Testing Suite | time: 30 minutes | han"
- Exception: "Billing software error | Inaccurate cost estimatio" ↔ "Customers may be upset or disappointed about not g" (sim=0.304291)
- Extra process: "preparing repair estimates"
- Extra process: "testing system functionality"
- Extra process: "ordering hardware components"
- Extra process: "informing customers"
- Extra process: "handling billing"

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 4 | Core activities—return without repair, hardware repair, software configuration, testing, billing/estimate, and returning the repaired computer—are all present. However, they are fragmented across multiple processes and some are duplicated or loosely specified. |
| Control Flow And Handoff Fidelity | 2 | The ground truth defines clear handoffs (most steps to Provide_Repair_Cost_Calculation; extended Billing → Testing → Return), but the reconstruction leaves most handoffs null or to 'customer' and does not reflect the prescribed chains. Sequencing is inconsistent with both variants. |
| Attribute Accuracy | 2 | Some tools and durations match (Hardware Diagnostic Tool at 1 hour; System Testing Suite at 30 minutes), but many times are missing, Software Configuration Utility is omitted, and billing durations/targets are wrong or absent. Handoffs and specific timing (10/15/20 minutes) are largely not captured. |
| Exception And Edge Case Capture | 5 | Both expected exceptions are captured with correct impacts and recoveries (hardware part unavailable; billing software error). Additional edge cases are included but do not detract from coverage of the required unhappy paths. |
| Faithfulness No Hallucination | 2 | The reconstruction introduces multiple new processes, steps, tools, and exceptions (supplier ordering system, informing customers, extra testing and communication flows) not in the ground truth. This adds considerable hallucinated content beyond the specified processes. |

## ElevenLabs

Reconstruction: `result_elevenlabs.json`

**Overall embedding similarity:** 0.491332
**Unmatched counts:** processes missed=1, extra=0; steps missed=2, extra=0; exceptions missed=0, extra=2

### Process alignment (truth[1] ↔ recon[0], aggregate=0.42515)
- Step: "Return_Repaired_Computer | tools:  | time: 10 minutes | hand" ↔ "Check new repair requests | tools:  | time:  | handoff: " (sim=0.734135)
- Step: "Billing | tools: Billing Software | time: 20 minutes | hando" ↔ "Calculate repair costs | tools: billing software | time: 15–" (sim=0.711726)
- Step: "Test_System_Functionality | tools: System Testing Suite | ti" ↔ "Repair and testing phase | tools:  | time: 1.5–2 hours per j" (sim=0.661089)
- Step: "Check_and_Repair_Hardware | tools: Hardware Diagnostic Tool " ↔ "Diagnose issues | tools:  | time: 2–3 hours per day | handof" (sim=0.602136)
- Missed step: "Return_Computer_Without_Repair | tools:  | time: 10 minutes | handoff: Provide_R"
- Missed step: "Check_and_Configure_Software | tools: Software Configuration Utility | time: 1 h"
- Exception: "Billing software error | Inaccurate cost estimatio" ↔ "Billing software glitches affecting cost estimatio" (sim=0.8272)
- Extra exception: "Waiting for hardware components to arrive | Delays repairs and the completion of"
- Extra exception: "Component failure after installation or miscommunication about a repair leading "
- Missed process: "Computer Repair Process"

### LLM judge (1–5)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Activity Coverage | 2 | Most expected steps are missing (e.g., Return_Computer_Without_Repair, Check_and_Repair_Hardware, Check_and_Configure_Software, Test_System_Functionality, Return_Repaired_Computer). Only cost calculation/billing is roughly represented, while extra generic steps were added. |
| Control Flow And Handoff Fidelity | 1 | The ground truth defines explicit handoffs and alternative paths, but the reconstruction provides no handoff targets and collapses phases, losing the defined sequencing in both processes. |
| Attribute Accuracy | 2 | For the one overlapping step, billing software and a 15–20 minute timeframe roughly match the 15 or 20 minutes in the ground truth, but other steps lack tools/times and no handoffs are specified, leading to weak detail fidelity. |
| Exception And Edge Case Capture | 4 | It captures both key exceptions semantically (parts unavailability causing delay; billing software errors with manual calculation and system update), though the hardware recovery omits the explicit 'order component' action. |
| Faithfulness No Hallucination | 2 | The reconstruction introduces non-ground-truth steps (checking new requests, diagnosis, combined repair/testing) and an extra exception about rework with its own recovery, indicating notable hallucination. |

---

*Embedding similarity uses greedy alignment by cosine similarity on field text. Judge scores are from a separate LLM comparison.*
