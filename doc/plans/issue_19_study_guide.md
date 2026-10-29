# Issue #19 Study Guide: One Console per March Unit

For someone new to this field. Behavior first, code last. Spec and decisions: `doc/plans/issue_19_convoy_console_per_march_unit_implementation_plan.md`;
reference text: `doc/scenario.md` ("One console per march unit").

## 1. The problem

In an autonomous convoy the trucks drive themselves, but a human still has to help when a truck is unsure what to do (a "decision event": a fork, a
contact, a lost track of the vehicle ahead). The simulator models that help as a **console**: a request goes in, waits its turn, is worked for a
while, and the answer comes back. A well-attended answer is high quality; no answer means the truck falls back to a poor local decision.

Before #19 the simulator had a single operator for the whole force, and it treated attention like this: attention = min(1, `span_capacity` / the number of ALL
Blue vehicles), worked out once at the start. For a 15-vehicle convoy and a capacity of 4 that is 0.27, so the operator's answers were only 77% as good as
possible, even though the real arrangement (ATP 4-11, M-5) is one commander per march unit with four trucks to look after. #19 gives each march unit its own console and
computes attention from the trucks that console actually looks after.

How it relates to the earlier work: #8 made march units, #14 added crew counts and the autonomous unit (one crewed control vehicle, four crewless trucks),
#17 decided what a unit does when its head dies. #19 uses all three: the console is hosted by the control vehicle, it serves the crewless trucks, and when the host
dies the #17 policy decides how the followers move.

## 2. Glossary

- **March unit**: a small group under one head (here: 1 control vehicle + 4 trucks).
- **Console**: one service station with its own queue. One per march unit.
- **Operator**: the commander at that console (on the control vehicle). Not shared with another unit.
- **Supervised agent**: a living vehicle of the unit with no assigned crew (the four trucks). The control vehicle is not one.
- **Request / decision event**: a truck asking its console for help.
- **Attention** = min(1, `span_capacity` / number of trucks the console looks after). 1.0 means the commander can follow all of them.
- **Quality** of an answered request = `q_auto` + (`q_operator` - `q_auto`) x attention. With attention 1.0 it is `q_operator` (0.95).
- **IT, WT, NT**: interaction time (service time of a request), wait time (time waiting in the queue), neglect time (time between a truck's last answer
  and its next request). The condition NT >= (s - 1)(IT + WT), with s the trucks per console, says the console can keep up.
- **Console loss**: the control vehicle is destroyed, so the console stops serving.
- **Communications delay / drop**: the link adds travel time and may lose a message. Separate from queueing and from attention.

## 3. Diagram

```
 march unit 0                 march unit 1                 march unit 2
 [H0] control vehicle         [H1] control vehicle         [H2] control vehicle
  |  hosts console 0           |  hosts console 1           |  hosts console 2
  v                            v                            v
 +-----------+                +-----------+                +-----------+
 | console 0 |                | console 1 |                | console 2 |   one queue each,
 | queue     |                | queue     |                | queue     |   one commander each
 +-----------+                +-----------+                +-----------+
  ^  ^  ^  ^                   ^  ^  ^  ^                   ^  ^  ^  ^
 [a][b][c][d]  crewless        [e][f][g][h]                 [i][j][k][l]
 trucks of unit 0              trucks of unit 1             trucks of unit 2
```

H0, H1, H2 (crewed) file no requests. Nothing in unit 1's queue can be served by console 0.

## 4. Worked example: three march units

Fifteen vehicles: three units, each with one manned control vehicle (H) and four unmanned cargo trucks. Capacity 4, quality 0.95 / 0.70, service rate 0.5
(2 steps per request), communications level C2 (one-way latency 2 steps, drop probability 0.10).

1. **Who files requests**: the 12 cargo trucks (a-l). H0, H1, H2 do not. Each truck has its own decision timer (about every 30 steps).
2. **Where they go**: truck b asks console 0, truck g asks console 1. They never share a queue.
3. **What the console does**: say trucks a, b, c, d of unit 0 ask on the same step. Each request travels 2 steps to console 0 (and may be lost with probability 0.10).
   Console 0 serves them one after another: waits of 0, 2, 4 and 6 steps, 2 steps of work each, then a 2-step trip home. Truck d sees 2 + 6 + 2 + 2 = 12 steps from request to answer.
   Unit 1's trucks, asking at the same moment, are unaffected.
4. **Attention**: each console looks after 4 trucks, so attention = min(1, 4/4) = 1.0 and the answer's quality is 0.95. With a capacity of 2 it would be 0.5 and the
   quality 0.825. Attention changes only that quality, never the waiting or the loss.
5. **Communications**: a lost request or reply sends the truck to its fallback quality 0.50 after its patience runs out (20 steps). That cost is independent of attention.
6. **If H1 is destroyed**: console 1 stops serving. Trucks e-h keep asking, nobody answers, they fall back to 0.50, and their movement follows the #17 policy (`halt` holds them,
   `continue` lets them drive on, `absorb` hands them to another unit). Consoles 0 and 2 are untouched.

## 5. What the metrics tell you

Per console you get requests, services, the three abandonment kinds (link, queue, console lost), IT, WT, NT, mean attention and a utilization (the share of time the console was busy).
Utilization is how busy a server was, **not** how hard the person was working. Pooled numbers divide only over consoles that were alive and had trucks to look after, so a
lost or empty console does not make the average look better or worse.

## 6. Sourced, assumed, and what the experiment says

**Sourced**: the idea that neglect time and interaction time bound how many robots one person can manage (Crandall et al. 2005, p. 438 and p. 440: fan-out = 1 + NT/IT); the
program setting of one manned leader and four unmanned followers (Army Sustainment 2021; ATP 4-11 M-5, pp. 81-82); that a future unit may be controlled by a human off the loop from a
tactical operations center (ATP 4-11 M-5). **Not found** in any source read: a numeric attention limit, a service rate, or an operator-to-vehicle ratio from the historical cases.

**Assumed**: crewed vehicles file no requests; the assignment of trucks to consoles never changes; a console dies with its control vehicle; no delay for any change of owner.

**Tests prove** the mechanism: routing and isolation, the attention formula and its bounds, loss and empty-unit behavior, and that duplicating an identical unit does not change another unit's console results.
**The experiment suggests** (30 seeds, one scenario): giving each unit its own console did not clearly change delivery or total Blue losses; it served a smaller share of requests than one
invulnerable operator, because the dedicated consoles are lost with their control vehicles; and worse communications mostly worked by dropping requests. Attention was 1.0 in every arm,
so the experiment does not test the attention term itself.

## 7. After the verification pass

**Unresolved assumptions (need approval):** (1) after a promote or an absorb the followers keep asking their original console even if it is dead; (2) vehicles that file no request keep quality 1.0, the best value on every scale; (3) exception routing is unit-tested but was never exercised in a mission run.

- **Exempt vehicles are better off, not just unpenalized.** The control vehicle (and any vehicle outside a unit) keeps quality 1.0, the top of every scale: it moves a little faster, shoots at full strength and is a slightly harder target than a supervised truck. It is also what a scenario without C2 gives everybody. Whether that is right is a decision for the Professor.
- **The attention formula was checked directly**, with no combat and a short fixed horizon: attention 1, 0.5 and 0.25 gave a served-decision quality of 0.95, 0.825 and 0.7625 exactly. It verifies the implemented equation; it does not validate a model of human workload. Note that the same quality number also slows vehicles and changes how well they shoot and how easily they are hit, so attention reaches movement and combat too. The first, longer run showed small differences in waiting between arms because all modules share one random stream and the paths diverge once the convoy meets Red; matched seeds do not keep matched request streams after that. The short run avoids it only for that scenario and horizon.
- **Dedicated assignment showed no effect in this tested setup.** With every control vehicle made indestructible in every arm and attention held at 1 (3 units, C0, 30 seeds, one scenario), one console per unit performed exactly like a pool of three consoles. That is an observation, not a general equivalence. The gain over a single operator comes from having more consoles. The earlier gap in served requests came from dedicated consoles dying with their control vehicles. The indestructible host is a diagnostic trick, not a remote-operator feature.
- **If the control vehicle dies**, the followers keep asking their dead console even if #17 promotes one of them or hands them to another unit. Nothing is re-assigned. That is an assumption waiting for approval.
- **NT, IT and WT** count only requests that were actually served; NT comes from completed intervals only, and open or interrupted gaps are left out. That censoring may be informative, so which way NT is biased is not established. A margin computed from averages (or pooled across consoles) does not prove that every console satisfies the inequality. The inequality NT >= (s-1)(IT+WT) comes from the issue, not from a source I could verify.
