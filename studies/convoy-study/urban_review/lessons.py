"""Plain-English lessons: symbols, substitutions and related real mission runs."""
INTRO={
 '9':('How much cargo actually arrived?','A surviving vehicle is not the same as a completed delivery. Separate delivered, lost and still-in-transit cargo.', [('L','Originally loaded cargo','tonnes'),('D','Delivered cargo','tonnes'),('X','Destroyed before delivery','tonnes'),('I','Alive but not delivered','tonnes'),('a_i','1 if vehicle i is alive, otherwise 0','binary'),('c_i','Original cargo on vehicle i','tonnes')],[46,44,45,0,1]),
 '12':('What does the convoy do when it receives fire?','Continue and halt are behavior choices. A halt timer is restarted by every new trigger.', [('k','Current simulation step','step'),('k_last','Step of the latest trigger','step'),('T_clear','Required time without another trigger','seconds'),('hold','Stop command, not a destruction state','boolean')],[11,9,27,10,8,26]),
 '13':('How does a vehicle follow a road around a corner?','Measure progress along the road, not the straight-line distance from its start.', [('s','Distance along the route','metres'),('r(s)','Position at route distance s','x,y coordinates'),('L','Total route length','metres'),('d_perp','Distance away from the route','metres')],[34,35,45,46]),
 '14':('How many people are exposed, and for how long?','Count people in living vehicles that are inside at least one eligible enemy weapon range. Accumulate that count over simulation steps.', [('i','One Blue vehicle','index'),('r','One Red shooter','index'),('k','One simulation step','index'),('n_i','Crew assigned to vehicle i','people'),('a_i,k','Alive=1, destroyed=0','binary'),('R_r','Enemy weapon range','metres'),('d_ir,k','Vehicle-to-enemy distance','metres'),('z_i,k','Inside at least one eligible range=1, otherwise 0','binary'),('E','Accumulated personnel exposure','crew-steps'),('dt','Duration of one step; 1 here','seconds')],[56,57,8,9,46]),
 '15':('How do settings become an experiment?','First make the objective and its units explicit. Then compare declared configurations across seeds; a weighted score is a preference, not physical truth.', [('J','Objective score; lower is better in this example','score'),('RS','Configured road space','metres'),('w_road','Chosen road-space penalty weight','score weight'),('road_scale','Normalization constant','metres')],list(range(47,56))),
 '16':('Can a building stop detection or firing?','A target can be close enough but hidden by a building. Optical line of sight is a separate gate from weapon range.', [('LOS','Clear line of sight=1, blocked=0','boolean'),('cell','Width of a raster cell','metres'),('(x,y)','A point in the world','metres')],[37,36,39,38]),
 '17':('What happens after the leader is destroyed?','Observe the loss, wait for the configured handoff delay, then appoint an eligible successor. These events are separate from console recovery.', [('k_loss','Step when the loss is observed','step'),('H','Configured handoff delay','steps'),('k_handoff','Earliest handoff step under the rule','step'),('leader=-1','This vehicle has no parent leader','identifier')],[22,21,20,23,24,25]),
 '18':('Why would Red choose a farther vehicle?','Priority chooses among eligible targets. A more important target can be farther away, but cannot bypass an eligibility restriction.', [('E','Set of eligible targets; not personnel exposure E','set'),('d_i','Shooter-to-target distance','metres'),('Control','Targets classified as control vehicles','set'),('argmin','Choose the target with minimum distance','operation')],[33,32]),
 '19':('How does one console serve a march unit?','Attention scales the gain in served quality above the autonomous baseline. Leadership recovery and availability of console service are separate mechanisms.', [('N','Assigned crewless followers per console','vehicles'),('C','Span capacity','vehicles'),('A','Attention factor, capped at 1','dimensionless'),('q_auto','Autonomous baseline quality','dimensionless'),('q_operator','Undiluted operator quality','dimensionless'),('q','Quality of a served decision','dimensionless')],[30,29,28,55])}

EXPOSURE=r'''
### 1. Decide exactly what is being measured

Exposure asks: **how many onboard people were inside an eligible enemy weapon range at each step?** It does not ask whether they were hit. An eligible Red shooter is alive, has weapon range greater than zero, and has `pk_base > 0`.

**Detection and line of sight are not required by this exposure metric.** A building can prevent firing while this particular range-based metric continues to count exposure. More than one covering enemy does not count the same crew twice.

### 2. Calculate distance first

Use a small teaching example: one enemy at (0,0), weapon range **R=100 m**. A control vehicle carrying **2 people** is at (60,80):

$$d=\sqrt{(60-0)^2+(80-0)^2}=\sqrt{3600+6400}=100\text{ m}.$$

Since 100 ≤ 100, it is inside the range, including the boundary: **z=1**.

An escort with **3 people** at (30,40) has:

$$d=\sqrt{30^2+40^2}=\sqrt{2500}=50\text{ m},\quad z=1.$$

A living cargo truck with **2 people** at (120,0) has:

$$d=\sqrt{120^2}=120\text{ m}>100\text{ m},\quad z=0.$$

### 3. Calculate the contribution of each vehicle in one step

$$e_k=\sum_i a_{i,k}\,n_i\,z_{i,k}.$$

| Vehicle | Alive a | Crew n | In range z | Contribution a × n × z |
|---|---:|---:|---:|---:|
| Control at (60,80) | 1 | 2 | 1 | 2 |
| Escort at (30,40) | 1 | 3 | 1 | 3 |
| Cargo at (120,0) | 1 | 2 | 0 | 0 |
| **Total this step** | | | | **5 crew-steps** |

$$e_k=(1\times2\times1)+(1\times3\times1)+(1\times2\times0)=2+3+0=5.$$

If the control vehicle is already destroyed at the measurement, its term becomes **0 × 2 × 1 = 0**, so that step would count only **3**. This is a separate illustrative condition, not an event claimed for the runs below.

### 4. Accumulate over time

$$E=\sum_k e_k,\qquad E_{seconds}=E\Delta t.$$

If the same living crews remain in those positions for **10 measured steps**:

$$E=5+5+\cdots+5=10\times5=50\text{ crew-steps}.$$

With dt=1 s this is **50 crew-seconds**. It is not 50 different people and not 50 casualties.

### 5. Now calculate a complete convoy, then watch it run

The two new diagnostic runs below use **18 vehicles**, three units, three escorts, a **100-second horizon**, and a deliberately huge Red range of **1,000,000 m**. Red lethality is almost zero but positive (`1e-15`), so it qualifies as a shooter while isolating exposure arithmetic. No vehicle was lost in these two executed runs. These are constructed diagnostics, not realistic combat parameters. The 100-second stop isolates exposure; it is not intended to complete the 60-tonne delivery mission.

| Vehicle role | Count | Manned crew per vehicle | Autonomous-cargo crew per vehicle |
|---|---:|---:|---:|
| Control | 3 | 2 | 2 |
| Cargo | 12 | 2 | 0 |
| Escort | 3 | 3 | 3 |

All are alive and inside range at each measurement, so a=1 and z=1:

$$e_{manned}=3(2)+12(2)+3(3)=6+24+9=39.$$

$$e_{auto}=3(2)+12(0)+3(3)=6+0+9=15.$$

After 100 measured steps:

$$E_{manned}=39\times100=3900\text{ crew-steps}.$$

$$E_{auto}=15\times100=1500\text{ crew-steps}.$$

The difference is **2400 crew-steps** under identical continuous range coverage. This demonstrates the arithmetic of different staffing, not a general reduction in per-person risk.

### 6. Connect the calculation to the actual run

Choose **Exposure diagnostic / Manned**, then use **1 s**, **10 s** and **100 s** below. The live calculation should show 39, 390 and 3900. Choose **Autonomous cargo** and repeat: 15, 150 and 1500.

The contribution table below comes from exact Python positions and the real metric update at each step. Contributions were checked against the engine's exposure increment for all 100 steps of both runs. It is not reconstructed from rounded display positions.

You can also select a saved natural-engagement run. In that case positions, deaths and time in range vary; use its recorded cumulative exposure instead of multiplying the initial crew count by the whole mission duration. Older traces do not contain the full per-vehicle audit, so the page does not invent one.

**Why is communications not a factor in the exposure equation?** Communications can affect behavior, position and survival through other rules. Those effects enter through a and z. This metric does not multiply exposure directly by C0–C5.
'''

def configure(examples,traces,sweep):
    for e in examples:
        question,meaning,symbols,runs=INTRO[e['issue']]
        e.update(question=question,meaning=meaning,symbols=symbols,related_runs=runs)
        if e['issue']=='14':
            e['lesson_markdown']=EXPOSURE
            e['validation_note']='Related verification: tests/test_convoy_autonomous_unit.py::test_full_range_equals_crew_times_steps_alive and test_crew_counted_once_per_step_with_many_shooters both passed. The two new 100-step diagnostic runs additionally audited every per-vehicle contribution against the engine.'
        elif e['issue']=='15':
            import math,statistics
            base=sorted([r for r in sweep['runs'] if r['arm']=='baseline'],key=lambda r:r['seed'])
            other=sorted([r for r in sweep['runs'] if r['arm']=='spacing_20'],key=lambda r:r['seed'])
            y=[r['result']['cargo_delivered'] for r in base];d=[b['result']['cargo_delivered']-a['result']['cargo_delivered'] for a,b in zip(base,other)]
            mean=statistics.mean(y);ss=sum((v-mean)**2 for v in y);sd=statistics.stdev(y);se=sd/math.sqrt(len(y));dm=statistics.mean(d);ds=statistics.stdev(d)/math.sqrt(len(d));interval=sweep['summary']['spacing_20']['cargo_delivered']['paired']
            assert abs(mean-sweep['summary']['baseline']['cargo_delivered']['mean'])<1e-9
            assert abs(se-sweep['summary']['baseline']['cargo_delivered']['se'])<1e-9
            e['symbols']=[('Y_s','Cargo delivered in seed s','tonnes'),('n','Number of seeds','runs'),('mean','Sum of results divided by n','tonnes'),('SD','Sample standard deviation across runs','tonnes'),('SE','Standard error of the mean','tonnes'),('delta_s','Arm minus baseline for the same seed','tonnes')]
            rows='\n'.join('| '+str(a['seed'])+' | '+str(a['result']['cargo_delivered'])+' | '+str(b['result']['cargo_delivered'])+' | '+str(dd)+' |' for a,b,dd in zip(base,other,d))
            e['lesson_markdown']=r"""### 1. Define one comparison

Use the saved direct-route experiment. The baseline is pace=10 m/s, time gap=4 s, spacing=40 m, C0. The comparison changes spacing to 20 m; all other inputs stay fixed. Both use seeds 0–9. These are actual saved results, not teaching numbers.

| Seed | Baseline delivered (t) | Spacing 20 delivered (t) | Paired difference (t) |
|---|---:|---:|---:|
"""+rows+rf"""

### 2. Calculate the baseline mean

Add the ten baseline deliveries: **{sum(y):g} tonnes** across ten runs. This sum is an intermediate calculation, not the cargo capacity of one convoy.

$$\bar Y={sum(y):g}/10={mean:g}\text{{ t}}.$$

### 3. Calculate variation and uncertainty

Subtract {mean:g} from each result, square each difference, and add them. The sum of squared deviations is **{ss:g}**.

$$SD=\sqrt{{{ss:g}/(10-1)}}={sd:.4f}\text{{ t}}.$$

$$SE=SD/\sqrt{{10}}={se:.4f}\text{{ t}}.$$

The reported mean ± SE is **{mean:g} ± {se:.2f} t**. SE describes uncertainty in the estimated mean, not the spread of an individual vehicle.

### 4. Pair the same seeds before comparing

For each seed, subtract baseline delivery from spacing-20 delivery. The ten differences sum to **{sum(d):g} t**:

$$\bar\delta={sum(d):g}/10={dm:g}\text{{ t}}.$$

The standard error of those paired differences is **{ds:.4f} t**. With 9 degrees of freedom, use t≈2.262:

$$CI_{{95\%}}=\bar\delta\pm2.262\,SE(\delta).$$

This gives approximately **[{interval['low']:.2f}, {interval['high']:.2f}] t**. The interval includes zero. A higher observed mean does not establish a best configuration, and including zero does not prove equivalence. These intervals are exploratory and unadjusted for multiple comparisons.

### 5. Watch the individual run, then return to the averages

The player below shows **seed 0**, not the mean of ten runs. Compare baseline and spacing-20 recordings to see their geometry, then use Results for the statistical comparison. Shared seeds do not guarantee identical request streams once trajectories diverge.
"""
            e['validation_note']='The arithmetic above was checked against the saved ten-seed experiment summary. The collapsed test source below verifies a separate #15 road-space objective penalty; it does not validate the mean or establish a best policy.'
        else:
            table='\n'.join('| '+s+' | '+m+' | '+u+' |' for s,m,u in symbols)
            steps='\n\n'.join('### '+str(i+1)+'. '+e['states'][i]['label']+'\n\n'+step for i,step in enumerate(e['steps']))
            e['lesson_markdown']='### Start with a small example\n\n'+e['setup']+'\n\n### Read the equation\n\n$$'+e['formula']+'$$\n\n'+steps+'\n\n### What this means\n\n'+e['limit']+'\n\n### Connect it to a related mission\n\nChoose a recording below and press Play. The worked numbers above belong to the small example; the mission can have different geometry, crew, delays or capacity. Its actual inputs and results are shown in the live calculation and configuration. A related mission illustrates the mechanism but does not isolate its causal effect.'
            e['validation_note']='The calculation above is supported by '+e['source']+'::'+e['node']+'. The existing verification run passed '+str(e['verified_cases'])+' case(s) for this function. Test code is supporting evidence, not the main lesson.'
