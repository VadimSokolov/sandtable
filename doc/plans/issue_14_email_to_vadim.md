**To:** Vadim Sokolov
**From:** Mark George
**Subject:** Issue #14 (autonomous march unit and personnel exposure): two decisions I need from you

Hi Vadim,

I read ATP 4-11 (16 March 2026) and implemented Issue #14 on branch `issue-14-convoy-autonomous-march-unit`
(not pushed). Where the issue left a choice, I took the simplest option. Two of those choices could change the
results, so I would like your decision on them. The other three are low risk.

**Need your decision**

1. **Escorts and the reference convoy.** ATP 4-11 G-7 counts every vehicle assigned to a march unit in its size
   (up to 25) and G-8 adds command and support vehicles on top of the task vehicles; G-10 and G-13 leave the
   security ratio to theater policy. Your Oct 20 crew ratios (2.6 and 2.1 for three to five escorts) only work if
   escorts are extra vehicles on top of the 15 cargo vehicles. The current code instead puts security vehicles
   into existing slots of the unit.
   - Implemented (simplest): no layout change; both arms use the same roles, so cargo count is equal.
   - Alternative: hold the cargo count fixed and let the unit grow with the number of escorts.
   - Which do you want for the paper's reference convoy?

2. **How the manned arm moves.** The one-page design says the arms differ in who rides and in what the followers
   depend on. ATP 4-11 G-11 and ATP 4-16 App. C describe a manned convoy as route, pace, order and gap, not
   independent navigation.
   - Implemented (simplest): the manned arm uses independent waypoint navigation, so the two arms also differ in
     column discipline.
   - Alternative: manned vehicles hold station on the vehicle ahead with human perception (no link or sensor
     loss), which isolates crew and follower dependence. This needs a small new follow mode.
   - Do you want the alternative?

**FYI, taken with the simplest option**

3. **Recovery crew = 2.** The issue gives no value. Public sources: M984 cab 2, M88A2 3. Security crew is 3 from
   secondary sources (CPP concept, CALL 18-10).
4. **"Red shooter"** = living Red with `weapon_range > 0` and `pk_base > 0`; each crew member counts once per
   step however many shooters cover the vehicle. I found no standard military metric matching this, so it is
   documented as a model-defined geometric exposure, not casualty risk.
5. **Control vehicle lost.** I found no public rule for what ATV-S followers do. ATP 4-11 does not say, and ADP
   6-0 covers human succession of command only. Implemented: an unmanned truck is never promoted to head
   (`succession = manned_only`; a manned security or recovery vehicle in the same unit may be). If none
   survives, followers take the existing waypoint fallback, and a counter `autonomous_headless_steps` shows how
   long that happens. A halt/continue policy and any escort re-tethering rule are #17's decision.

**Observations from a first run (10 seeds, uc3 convoy, equal cargo count, no escorts)**
Crew-steps at risk fall from about 3,550 (manned) to about 650-720 (autonomous), and outcomes do not change with
the comms rung C0 to C5 in this scenario. Treat both as preliminary: the manned arm is waypoint-driven (item 2),
Red does not prioritise the control vehicle (#18), and the c2 attention term is unchanged (#19).

**Caveats on sources:** ATP 4-01.45 and TC 4-11.46 are restricted and I did not read them. Crew and ratio
figures other than ATP 4-11 come from secondary sources.

Details: `doc/plans/issue_14_convoy_autonomous_march_unit_implementation_plan.md` and
`doc/plans/issue_14_open_questions_ar.md`.

Thanks,
Mark
