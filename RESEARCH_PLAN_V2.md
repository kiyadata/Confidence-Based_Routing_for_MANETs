# Confidence-Aware OLSR: Exploring the Reliability-Routing-Cost Trade-off in Dynamic MANETs
Research plan v2. This replaces the framing of the first roadmap and keeps the files from IMPLEMENTATION_GUIDE.md where noted.

----------------------------------------------------------------------
## 1. Research question and hypotheses

Research question
  Can dynamically estimated node confidence be integrated into OLSR to improve packet-delivery reliability while maintaining an acceptable trade-off among path length, end-to-end delay, routing overhead and route stability?

Hypotheses
  H0  Standard OLSR is sufficient. Confidence gives no reliability gain that justifies its routing cost.
  H1  Dynamic confidence-aware OLSR raises delivery reliability and reduces use of unreliable relays, while the increase in path length, delay, overhead and route changes stays within pre-defined limits.

Secondary question (the one that makes the paper interesting)
  Under what network conditions (mobility, density, fraction of unreliable nodes, confidence volatility) does confidence-aware routing give a net benefit, and where does it stop being worth its cost?

----------------------------------------------------------------------
## 2. What changed from the first roadmap

  Old                                              New
  Estimator-reported score, static scenarios       Dynamic confidence, updated from observed forwarding (EMA)
  Compare cost functions, report useful delivery   Reliability vs cost trade-off, Pareto view, PDR as headline metric
  No stability mechanism required                  Hysteresis is part of the design, route changes are a measured outcome
  Fixed alpha                                      alpha swept, plus an adaptive-alpha variant
  Hard threshold as a baseline                     Threshold is a soft penalty, so a bad node can still be used when avoiding it is too costly
  Success = fewer bad relays                       Success = reliability gain WITHOUT unacceptable cost, with "unacceptable" defined before the runs

Two things from the first roadmap are kept on purpose
  - The sanity requirement: with confidence neutral (alpha = 0, or all c = 1), the system must reproduce stock OLSR exactly. The prototype now checks this automatically.
  - The diamond test as the first ns-3 check.

----------------------------------------------------------------------
## 3. A tension you need to resolve in the paper (read this)

The earlier novelty argument rested on confidence being self-assessed from an internal estimator (Kalman filter, positioning), which separates it from trust-based routing.
The new plan computes confidence from observed forwarding behaviour. That is much closer to trust and reputation OLSR, which the material you pasted correctly says is already well studied.

So the claim "we add confidence to OLSR" is not enough, and the plan's answer is right: the contribution has to be the characterization of the trade-off (when it pays off, at what cost), plus the mechanisms that make dynamic confidence usable (hysteresis, adaptive weighting, recovery of avoided nodes).

Two ways to keep a clearer differentiator, pick one and say so
  A. Keep confidence generic: C_i can come from forwarding success (this plan) OR from an estimator (the first plan). Show the same routing layer works with both. Estimator-agnostic is then a real contribution.
  B. Go fully behavioural, and position against trust-based OLSR with a comparison table (what is measured, how it is updated, what trade-offs are studied). Do a proper literature search first and cite the trust-based OLSR work directly.

Literature check result (see LITERATURE_REVIEW.md): the name "confidence-aware OLSR" already appears in published work (TCAOLSR and OLSRT-C, both attack-focused), trust plus hop count in one OLSR route choice exists (TUE-OLSR), reputation fading covers the recovery idea, and link-level hysteresis already exists in OLSRd. Plan the paper around the trade-off characterization, the estimator-agnostic interface and route-level hysteresis, and verify the full texts listed in the to-do section before claiming any gap.

Also, the pasted text gives novelty scores and publication odds. Treat those as one opinion. Nobody can know them before your results exist, and I would not put any number like that in your plans. The checks that matter are the seven results listed in section 10.

----------------------------------------------------------------------
## 4. System design

Architecture
  Normal OLSR  ->  Confidence estimation  ->  Confidence-aware route cost  ->  Hysteresis  ->  Final route
  OLSR stays OLSR: same messages, same flooding, same MPRs. Only the metric used to choose routes changes, plus one confidence field in control messages.

4.1 Dynamic confidence (per node, every step, default 1 s)
    C_i <- lambda * C_i + (1 - lambda) * F_i
    F_i = packets successfully forwarded / packets this node was asked to forward, during the step
    lambda = 0.8 by default (higher means slower, smoother)
    No traffic during a step:  C_i <- C_i + recovery * (1 - C_i)
  Worked example from the notes: old 0.80, recent success 0.40, lambda 0.8 gives 0.8 * 0.8 + 0.2 * 0.4 = 0.72.

  Why recovery is needed (this is a real finding from the prototype logic, worth a paragraph in the paper)
  If routing avoids a node, that node carries no traffic, so it gets no observations, so its confidence can never rise again. A slow drift toward 1 lets it be re-tested. It also creates a mild explore/exploit oscillation, which hysteresis then damps. Study recovery as a parameter.

  Extension for later: a richer score C = w_f F + w_s S + w_l L + w_r R (forwarding, stability, link quality, recency). Start with the single EMA.

4.2 Route cost (cost of entering a relay v; the destination is not penalised)
    olsr          base
    add           base + alpha * (1 - C_v)
    mult          base * (1 + alpha * (1 - C_v))
    threshold     base + alpha  if C_v < thr, else base      (soft penalty, node can still be used)
    add-adaptive  additive, with alpha growing with the share of known low-confidence nodes
  base = 1 (hop count, as in stock ns-3 OLSR) or ETX.

  Important detail: if base is hop count (every base = 1), add and mult are algebraically the same. The prototype shows identical numbers for them. To compare add against mult you must use ETX as the base. This is one more reason to implement ETX in ns-3 (Option B in IMPLEMENTATION_GUIDE.md, Stage 3).

4.3 Hysteresis
  Replace a working route only if  Cost_new < Cost_current * (1 - H).  Test H = 0, 0.05, 0.10, 0.15.
  A broken route is always replaced.

4.4 Adaptive alpha
    alpha = alpha_lo + (alpha_hi - alpha_lo) * min(1, known_low_fraction / frac_ref)
  Small penalty in a healthy network, large penalty when many nodes look unreliable.

4.5 Packet format
  Same as the first plan: confidence byte plus age plus a validity flag, carried in the OLSR HELLO and TC reserved bits (zero extra bytes) and, for the overhead analysis, in a TLV variant. See IMPLEMENTATION_GUIDE.md Stage 5A.

----------------------------------------------------------------------
## 5. Define "acceptable" BEFORE you run experiments

Write these down, with a justification, then do not change them after seeing results.

  PDR improvement           at least 5% relative         (placeholder, justify from your application)
  Delay increase            at most 10%
  Average hop increase      at most 15%
  Routing overhead increase at most 10%
  Route changes             report, and compare with and without hysteresis

The prototype takes these as flags: --min-gain, --max-delay-inc, --max-hop-inc.
Do a sensitivity analysis with several threshold sets, and always show the Pareto frontier, so the conclusion does not hinge on one arbitrary line.

Observation from the first prototype run: with these placeholder limits, 24 of 32 configurations passed. A test that most configurations pass is not discriminating. Either tighten the limits with a real justification or lean on the Pareto frontier.

----------------------------------------------------------------------
## 6. Experiment matrix

Original table from the notes, mapped to the prototype flags (run each with 30 seeds)

  E1   20 nodes   0 m/s    0% fragile   --nodes 20  --speed 0   --fragile 0
  E2   20 nodes   5 m/s   10%           --nodes 20  --speed 5   --fragile 0.10
  E3   20 nodes  15 m/s   25%           --nodes 20  --speed 15  --fragile 0.25
  E4   50 nodes   5 m/s   25%           --nodes 50  --speed 5   --fragile 0.25
  E5  100 nodes   5 m/s   25%           --nodes 100 --speed 5   --fragile 0.25
  E6   50 nodes   5 m/s   50%           --nodes 50  --speed 5   --fragile 0.50
  E7-E10  alpha = 1, 2, 4, 8 in E4's setting     --alphas 1 2 4 8

Add these, since they answer the secondary question
  confidence volatility    --volatility 0.5 1 2
  hysteresis               --hyst 0 0.05 0.10 0.15
  recovery rate            --recovery 0 0.01 0.02 0.05
  base metric              --base hop  and  --base etx

Example batch
  for f in 0 0.1 0.25 0.5; do
    python3 prototype/uar_dynamic.py --trials 30 --base etx --fragile $f \
        --csv prototype/raw_f$f.csv --plot prototype/figs_f$f
  done

Metrics
  PDR, mean hop count, mean delay, control overhead (bytes, packets), route changes per minute, share of traffic through really-low-reliability relays.
  The prototype covers all except overhead (that comes from ns-3 and from the formula in IMPLEMENTATION_GUIDE.md).

----------------------------------------------------------------------
## 7. What the prototype already shows (preliminary, toy model)

Setting: 50 nodes, 25% fragile, 5 m/s, ETX base, 20 seeds, 300 s, same movement and same random draws for every configuration.

  Standard routing:              PDR 0.673, share through bad relays 31.2%, route changes 5.07 per flow per minute
  Additive, alpha 8, H = 0:      PDR 0.817 (+21%), delay +9.1%, hops -1.5%, bad-relay share 6.8%, route changes 5.42
  Additive, alpha 8, H = 0.1:    PDR 0.812 (+20.6%), delay +9.7%, route changes 3.50 (about a third fewer than H = 0)
  Additive, alpha 4, H = 0:      PDR 0.802 (+19%), delay +7.7%
  Additive, alpha 1, H = 0:      PDR 0.752 (+11.7%), delay +4.8%
  Adaptive alpha, H = 0:         PDR 0.779 (+15.7%), delay +6.3%

Pattern worth testing for real
  - Gains rise quickly from alpha 1 to 4, then flatten around 8 to 16. That is the "useful operating region" story in your notes, appearing in a model.
  - Hysteresis cuts route changes at almost no reliability cost.
  - Additive, multiplicative and soft-threshold cost functions end up close to each other in this model. Do not expect a dramatic winner.
  - Adaptive alpha did not beat a well-chosen fixed alpha here. That is a legitimate finding: report it honestly.

Why you must not quote these as results
  - Fragile nodes drop packets in a way I defined (true reliability drives drops). Real behaviour differs.
  - Delay is a proxy (expected MAC attempts times 5 ms, plus 2 ms per hop), over delivered packets only.
  - Overhead is not modelled.
  - Confidence is self-observed with no neighbour watchdog and no cheating nodes.
  These numbers justify building the ns-3 version. They are not the evidence for the paper.

----------------------------------------------------------------------
## 8. Implementation order (updated)

  Phase 1  Python prototype              DONE. prototype/uar_dynamic.py (v2) and prototype/uar_prototype.py (v1, estimator-state scenario)
  Phase 2  ns-3 baseline                 ns3/uar-baseline.cc. Run stock OLSR, record PDR, delay, hops, control bytes. Do not modify OLSR yet.
  Phase 3  Dynamic confidence module     ns3/uar-confidence-manager.h (new). True reliability, fault injection, EMA confidence.
  Phase 4  Give confidence to OLSR       reserved-bits field in HELLO/TC, receiver confidence table (IMPLEMENTATION_GUIDE.md Stage 5A, 5B)
  Phase 5  Modify route calculation      Dijkstra with the additive cost first (Stage 5C). One formula working before the others.
           Add hysteresis here.
  Phase 6  Diamond test                  ns3/uar-diamond.cc. Use UarConfidenceManager::ForceTrueReliability for A and B
                                         (or the older Force() in uar-confidence-model.h). Expected: route follows the better node, and does not flip on tiny changes.
  Phase 7  Dynamic test                  Degrade A step by step 0.9 -> 0.3, route moves away. Recover A, route returns after the hysteresis margin.
  Phase 8  Experiments                   matrix in section 6, 30 seeds each
  Phase 9  Analysis                      mean, standard deviation, 95% confidence interval, paired comparisons, Pareto plots

Where fault injection goes in ns-3
  In the modified OLSR forwarding path, at the point where a node forwards a transit data packet (not one it originated, not one for itself):
      if (UarConfidenceManager::ShouldDrop(nodeId)) { drop; return; }
  If you do not drop packets, PDR cannot respond, and your headline metric will show nothing.
  Log TrueReliability(nodeId) for every relay a packet uses. That gives the "share through really-low-reliability relays" metric from ground truth.

----------------------------------------------------------------------
## 9. Paper outline (updated)

Title
  Confidence-Aware OLSR: Exploring the Reliability-Routing-Cost Trade-off in Dynamic MANETs

Abstract skeleton
  Standard OLSR chooses routes with metrics that ignore how reliably a node forwards over time. We integrate a dynamically estimated node confidence, updated by an exponential moving average of observed forwarding success, into OLSR route selection through an additive penalty, with hysteresis to limit route changes. Rather than only maximizing delivery, we quantify the reliability-routing-cost trade-off across density, mobility, fraction of unreliable nodes and confidence volatility, using ns-3 with [N] seeds per setting. Results show [X% PDR improvement] at [Y% added delay], [Z% added hops] and [W% added control overhead], and identify the conditions under which the benefit disappears. [Fill in real numbers only.]

Contributions
  1. A lightweight dynamic confidence estimate and its integration into OLSR route cost.
  2. A study of confidence integration strategies (additive, multiplicative, soft threshold, adaptive weighting).
  3. A hysteresis mechanism for the instability that dynamic confidence introduces, with measured effect.
  4. A reliability-versus-cost characterization (Pareto frontier) and the conditions under which confidence-aware routing is or is not worthwhile.

Sections
  1 Introduction   2 Related work (trust-based OLSR, link-quality metrics, energy-aware routing; comparison table)   3 System model and problem statement
  4 Design (confidence, cost, hysteresis, adaptive alpha, packet format)   5 Overhead analysis   6 Simulation setup   7 Results (by research question)   8 Limitations   9 Conclusion

Threats to validity (write this section honestly)
  - Fault model is injected, not measured from real hardware
  - Honest self-reporting assumed, no malicious nodes
  - One routing protocol, one radio model
  - Acceptability limits are choices, shown with sensitivity analysis

----------------------------------------------------------------------
## 10. What would make the results convincing

  1. PDR improves significantly when nodes become unreliable.
  2. The gain is not just from absurdly long detours (hops and delay stay bounded).
  3. Delay increase stays within the pre-defined limit.
  4. Routing overhead does not explode.
  5. Hysteresis reduces route changes.
  6. The effect holds at 20, 50 and 100 nodes and at several mobility levels.
  7. The improvement is statistically significant across at least 30 seeds, with paired comparisons.
  Report the cases where it fails (sparse networks, very high mobility, very fast confidence changes). Those cases are part of the contribution.

----------------------------------------------------------------------
## 11. Update: final framing and prototype changes

Final research question
  Under what network conditions does dynamically confidence-aware OLSR provide a net reliability benefit, and how can adaptive weighting and route-level hysteresis maximize that benefit without excessive routing cost?

Working title
  Confidence-Aware OLSR: Characterizing the Reliability-Routing-Cost Trade-off in Dynamic MANETs
  (the phrase "confidence-aware OLSR" overlaps published work; see LITERATURE_REVIEW.md; alternative: Reliability-Cost Trade-offs of Dynamic Node-Confidence Routing in OLSR-Based MANETs)

Contributions
  1. A dynamic node-confidence mechanism that updates reliability from recent behaviour.
  2. A confidence-aware OLSR cost that trades confidence against path cost (soft penalty, not a ban).
  3. Adaptive confidence weighting driven by network conditions.
  4. Route-level hysteresis for confidence-driven route changes.
  5. A systematic characterization of reliability versus delay, hops, overhead and stability across density, mobility, unreliable-node fraction, confidence volatility, alpha and hysteresis, summarized as a decision map.

Changes made to the prototype
  - alpha = 0 is part of the sweep (it must reproduce plain routing exactly; checked automatically)
  - a fair baseline "olsr(H=...)" (plain routing with the same hysteresis). Hysteresis calmed plain routing too (5.05 to 2.98 route changes per minute), so judge confidence-specific stability against that baseline
  - an analytical overhead estimate and event-triggered update counting (parameters are assumptions, replace with ns-3 measurements)
  - an alpha-sweep summary that marks the knee (alpha 8 in the reference run)
  - uar_boundary.py: decision map over speed and unreliable-node fraction, with a paired significance check. An absolute route-change allowance was added after the first run showed that a static network (zero baseline route changes) made every change look unstable. Report it as a design choice
  - flapping_demo.py: two near-equal routes, 17 switches without hysteresis versus 0 with a 10 percent margin in 120 s

Findings so far that complicate the story (report them honestly)
  - Adaptive alpha did not beat a well-chosen fixed alpha (+15.9 versus +21.3 percent PDR gain)
  - Hysteresis is not specific to confidence; the confidence-specific effect is that confidence-aware routing still changes routes somewhat more than plain routing with the same margin (3.51 versus 2.98 per minute)
  - At 50 percent unreliable nodes the gain is large (37 to 43 percent) but delay exceeds the placeholder 10 percent limit, so acceptability limits drive the conclusion; justify them or show the whole frontier
