# UAR-Mesh: Implementation Guide
Confidence-Based Routing for Mobile Ad Hoc Networks

> UPDATE: the research focus changed. Read RESEARCH_PLAN_V2.md first (new research question, dynamic confidence,
> hysteresis, Pareto evaluation). This guide still holds for installing ns-3, the baseline run, the OLSR packet
> changes (Stage 5A, 5B), the route-calculation change (Stage 5C) and the diamond test. Where the two differ,
> follow RESEARCH_PLAN_V2.md. New files: prototype/uar_dynamic.py and ns3/uar-confidence-manager.h.

This guide takes you from zero to a working experiment, in the order you should do things. Read the whole thing once, then work stage by stage.

Files in this folder
  IMPLEMENTATION_GUIDE.md              this file
  prototype/uar_prototype.py           Python test of the core idea (runs now, no ns-3 needed)
  prototype/results_random.csv         output of that script, random low-confidence nodes
  prototype/results_clustered.csv      output of that script, clustered low-confidence nodes
  ns3/uar-baseline.cc                  ns-3 baseline scenario (OLSR or AODV, no confidence yet)
  ns3/uar-confidence-model.h           ns-3 confidence source model (makes c(t) for each node, has Force() for tests)
  BEGINNER_ROADMAP.md                  every step explained in plain language, with a teacher presentation plan
  LITERATURE_REVIEW.md                 closest prior work, comparison table, verification to-do list
  prototype/uar_boundary.py            decision map: when is confidence-aware routing worth it
  prototype/flapping_demo.py           10-second demonstration of route flapping and hysteresis
  prototype/demo_outputs/              results and figures from the runs described in the roadmap
  RESEARCH_PLAN_V2.md                  revised research question, design, experiments, paper outline (read first)
  prototype/uar_dynamic.py             dynamic prototype: EMA confidence, hysteresis, adaptive alpha, Pareto analysis
  prototype/results_dynamic_etx_f25.csv and figures_dynamic/   output of one 20-seed run
  ns3/uar-confidence-manager.h         ns-3 dynamic confidence: true reliability, fault injection, EMA
  ns3/uar-diamond.cc                   ns-3 diamond-topology test: does the route follow the confidence?
  analysis/analyze_results.py          turns your results CSV into summary tables and the paper plots (tested on demo data)

Honesty note: the Python prototype was run and tested. The ns-3 files were written carefully but could not be compiled where they were produced, so expect small API fixes. The OLSR patch in Stage 5 is a plan with snippets, not finished code.

----------------------------------------------------------------------
## The overall flow in one picture

  Stage 1  Python prototype      prove the idea works on paper (graphs only)
  Stage 2  Install ns-3          get the simulator running
  Stage 3  ns-3 baseline         measure normal OLSR/AODV (your comparison point)
  Stage 4  Confidence model      give each simulated node a confidence c(t)
  Stage 5  Modify OLSR           advertise c, use it in route cost  (hardest part)
  Stage 6  Experiments           many runs, many settings, save CSVs
  Stage 7  Plots and paper       figures from the CSVs

Do not skip Stage 1. It is cheap, it tells you which cost function to pick, and it gives you a reference to check ns-3 against later.

----------------------------------------------------------------------
## Stage 1: Run the Python prototype (about 1 hour)

Requirements: Python 3.8+, nothing to install.

  cd prototype
  python3 uar_prototype.py
  python3 uar_prototype.py --nodes 100 --trials 50 --pattern clustered
  python3 uar_prototype.py --alpha 8 --csv my_results.csv

What it does
  1. Scatters nodes in a square, links nodes within radio range, gives each link an ETX.
  2. Marks a fraction of nodes as low confidence (c between 0.05 and 0.40), the rest high (0.85 to 1.0).
  3. Routes random flows under five cost functions: etx, add, mult, threshold, adaptive_alpha.
  4. Reports, averaged over trials with 95% confidence intervals:
       delivered     fraction of flows that still found a route
       low-relay%    fraction of delivered flows that pass through a low-confidence relay
       useful        average of (product of relay confidences), counting undelivered flows as 0
       ETX, hops     path quality and length

The sanity check at the top confirms the key design requirement: when every confidence is 1, add/mult/threshold/adaptive_alpha produce exactly the ETX baseline.

The final comparison table reports the best confidence-aware strategy per low-confidence fraction against the ETX baseline. `adaptive_alpha` uses an additive confidence penalty whose weight grows from `--alpha-lo` to `--alpha-hi` as the observed low-confidence fraction approaches `--frac-ref`.

What the first run showed (30 trials, 50 nodes, random pattern)
  - At 25% low-confidence nodes, plain ETX sends 58.5% of flows through at least one low-confidence relay. mult cuts that to 25.3%, and add to 26.0%.
  - Useful delivery at 25%: etx 0.423, mult 0.646, add 0.649.
  - The price: path ETX rises from 9.92 (etx) to 10.81 (mult).
  - threshold removes low relays entirely but disconnects flows: delivery drops to 0.912 at 25% and 0.705 at 50%.

How to read this
  - mult and add are the moderate options: big drop in bad relays, small extra cost.
  - threshold shows the danger of a hard cutoff, and is a nice argument for a soft penalty in your paper.
  - Treat these as preliminary results from a toy model. The paper's numbers come from ns-3.

A caveat you must handle in the paper
  The "useful" metric is a product over relays, so it naturally rewards paths with fewer relays. That is why the hop-count mode scores well on "useful" even with no confidence awareness. Always compare a confidence-aware variant against its own link-metric baseline (etx), not against hop. Also report low-relay% next to useful, since it does not have this bias.

Experiments to try in Stage 1
  - Sweep alpha: 0, 1, 2, 4, 8, 16. Plot useful and ETX against alpha. Pick the knee.
  - Compare patterns: random vs clustered.
  - Compare network sizes: 20, 50, 100.
  - Make sparse networks (--range 150) and watch threshold collapse.

----------------------------------------------------------------------
## Stage 2: Install ns-3 (about 1 to 2 hours)

Use Linux (Ubuntu 22.04 or 24.04, or WSL2 on Windows). Commands below use 3.40 as the example. Get the latest release from nsnam.org and keep the same steps.

  sudo apt update
  sudo apt install g++ python3 cmake ninja-build git ccache make
  wget https://www.nsnam.org/releases/ns-allinone-3.40.tar.bz2
  tar xjf ns-allinone-3.40.tar.bz2
  cd ns-allinone-3.40/ns-3.40
  ./ns3 configure --enable-examples --enable-tests
  ./ns3 build              # first build takes a long time, 20 to 60 minutes

Check it works
  ./ns3 run first
  ./ns3 run "manet-routing-compare --protocol=2 --nWifis=20"   # 2 = OLSR

If manet-routing-compare runs and prints results, your setup is good. Read that example's source: your scenario is a simplified version of it.

----------------------------------------------------------------------
## Stage 3: Run the baseline scenario (about 1 day)

  cp ns3/uar-baseline.cc  <ns-3 folder>/scratch/
  ./ns3 run "uar-baseline --proto=olsr --nNodes=30 --speed=5 --run=1"

You should see one line: PDR, mean delay, control bytes. It also appends to baseline.csv.

Things to check
  - PDR above 0: if it is 0, nodes are out of radio range. Shrink --area (try 200) or raise --txPower. Default Wi-Fi range is only tens of metres.
  - Change --run to 2, 3, 4 and see results vary. That is how you get multiple seeds.
  - Try --proto=aodv.

Run a batch (bash)
  for run in $(seq 1 20); do
    ./ns3 run "uar-baseline --proto=olsr --nNodes=30 --run=$run --outCsv=olsr_base.csv"
  done

The control overhead number comes for free: OLSR runs on UDP port 698 and AODV on 654, and the script sums those flows.

Decide here which protocol you build on. Recommendation: OLSR.
  - Proactive, so a node learns other nodes' scores before a flow starts.
  - HELLO and TC messages already carry per-node information.
  - Fewer moving parts than AODV's request/reply cycle.

Important fact: the stock ns-3 OLSR routes by hop count, not ETX. Two options
  A. Keep hop count as the base metric. Your cost becomes sum over hops of (1 + alpha * (1 - c)). Baselines: hop-count OLSR vs confidence-aware OLSR. Simplest, and fully honest.
  B. Add ETX measurement to OLSR (count HELLOs received per neighbour over a window, give each link ETX = 1 / (p_forward * p_reverse)). More work, more realistic, and lets you claim "ETX baseline".
Start with A, finish the whole pipeline, then upgrade to B if time allows.

----------------------------------------------------------------------
## Stage 4: Add the confidence model (about 1 day)

  cp ns3/uar-confidence-model.h  <ns-3 folder>/scratch/

In your scenario (a copy of uar-baseline.cc, call it uar-mesh.cc):

  #include "uar-confidence-model.h"
  ...
  // after nodes.Create(nNodes):
  double fragileFraction = 0.25;          // add as a command-line parameter
  UarConfidenceModel::Install(nNodes, fragileFraction, 1.0);

Anywhere you need a node's confidence:
  double c = UarConfidenceModel::Get(node->GetId());   // 0..1
  uint8_t wire = UarConfidenceModel::GetByte(node->GetId());   // 8-bit value for the packet

How the model behaves
  - fragileFraction of nodes are fragile. A fragile node randomly enters a degraded state (target c between 0.05 and 0.40) and later recovers.
  - Other nodes stay near 1.
  - c moves smoothly toward its target, so it never jumps instantly (good, because jumps cause route flapping).
  - Output is quantized to 8 bits, the same as the packet field.

Test it: print Get(i) for a few nodes every 10 seconds with Simulator::Schedule and confirm the fragile nodes dip and recover.

Upgrade for the paper
  Replace the random process with real covariance or error logs from a state estimator, sampled at your update rate. That answers the "your confidence is fake" objection.

----------------------------------------------------------------------
## Stage 5: Modify OLSR (about 2 to 4 weeks, the hard part)

Work on a copy so you never break the stock module.

  cd <ns-3 folder>/src
  cp -r olsr uar-olsr
  # rename: files olsr-*.{h,cc} to uar-olsr-*.{h,cc}, namespace olsr to uar_olsr,
  # class names RoutingProtocol -> UarRoutingProtocol, helper OlsrHelper -> UarOlsrHelper,
  # update uar-olsr/CMakeLists.txt, then:
  ./ns3 configure && ./ns3 build

Get the rename building and passing a baseline run (identical to stock OLSR) BEFORE you change any behaviour. Test: results of uar-olsr with all c = 1 must match stock olsr for the same seed.

If renaming the whole module feels too heavy, edit src/olsr directly in a git branch. It is less clean but much faster to get going, and you can restructure later.

### 5A. Put confidence in the packet

OLSR HELLO and TC messages each contain a 16-bit "reserved" field (RFC 3626 says it must be sent as zero and ignored on receipt). Using it gives a zero-extra-byte, backward-compatible prototype.

  HELLO fixed part (4 bytes):   | reserved 16 bit | Htime 8 | Willingness 8 |
  TC fixed part (4 bytes):      | ANSN 16 bit     | reserved 16 bit        |

Plan: split the 16 reserved bits into
  bits 15..8   confidence (0..255, maps to 0.0 to 1.0)
  bits  7..1   age, in units of 1 second (0..127), time since confidence was computed
  bit   0      flag: 1 = estimator unavailable (ignore the confidence value)

Where to edit (file names as in ns-3's olsr module; check your version)
  olsr-header.h / .cc, class MessageHeader::Hello and MessageHeader::Tc:
    - add members:  uint8_t confidence; uint8_t confAge; bool confValid;
    - Serialize:    replace i.WriteHtonU16(0)  with  i.WriteHtonU16(PackConf(...))
    - Deserialize:  replace the skipped reserved read with  UnpackConf(i.ReadNtohU16())
    - GetSerializedSize: unchanged, because the field already exists. That is the point.

Helper functions
  uint16_t PackConf(uint8_t c, uint8_t age, bool valid)
  {
      return (uint16_t(c) << 8) | (uint16_t(age & 0x7F) << 1) | (valid ? 0 : 1);
  }
  void UnpackConf(uint16_t v, uint8_t& c, uint8_t& age, bool& valid)
  {
      c = v >> 8;
      age = (v >> 1) & 0x7F;
      valid = !(v & 1);
  }

Limits of this trick (mention them in the paper)
  - It adds no bytes, so overhead analysis for this variant shows 0 extra bytes. For the paper, also define a proper TLV-style extension (type, length, 1 to 2 value bytes) as a second variant and report its overhead. OLSRv2 (RFC 7181) uses TLVs, which is the natural precedent.
  - A node's confidence reaches the network only through messages the node originates. HELLO covers one-hop neighbours. TC is originated only by nodes that are selected as MPRs, so confidence of other nodes is not learned network-wide. Either let every node send TC, or accept partial knowledge and measure its effect. State your choice.

### 5B. Send and store it

In the routing protocol file (olsr-routing-protocol.cc):

  Sender side, in SendHello() and SendTc():
      uint32_t id = m_ipv4->GetObject<Node>()->GetId();
      msg.GetHello().confidence = UarConfidenceModel::GetByte(id);
      msg.GetHello().confAge    = 0;
      msg.GetHello().confValid  = true;
      // same for Tc

  Receiver side, in ProcessHello() and ProcessTc():
      m_confTable[msg.GetOriginatorAddress()] = { confidence, Simulator::Now() };
      // m_confTable: std::map<Ipv4Address, ConfEntry>, ConfEntry = {uint8_t c; Time t;}

  Reading a score (the one function the rest of the code uses):
      double GetConf(Ipv4Address node)
      {
          auto it = m_confTable.find(node);
          if (it == m_confTable.end()) return 1.0;                  // unknown: neutral default
          if (Simulator::Now() - it->second.t > Seconds(3 * helloInterval)) return 1.0;  // expired
          return it->second.c / 255.0;
      }
  Choose the default for unknown or expired scores on purpose, and test both 1.0 (optimistic) and a lower value (pessimistic).

Event-triggered variant (for the overhead experiments)
  Send a new value only when |c_now - c_last_sent| > delta, or after a maximum silence period. In the reserved-field design every message has the field anyway, so the saving appears only with the TLV variant, where the TLV is simply omitted when unchanged.

### 5C. Use it in the route cost (the real change)

Stock ns-3 OLSR builds its table in RoutingProtocol::RoutingTableComputation(). It grows routes by hop count: neighbours first, then 2-hop neighbours, then topology entries one hop at a time. That loop cannot express weighted costs. Replace it with Dijkstra over the link-state graph.

Pseudo-code
  build graph G:
      vertices = this node + all addresses in the neighbour set, 2-hop set, topology set
      edges    = symmetric links to 1-hop neighbours, 2-hop links, topology tuples (last -> dest)
  for each edge (u -> v):
      base = 1.0                       // hop count   (Option A)
             or ETX(u,v) if you have it // Option B
      if v is not the destination being evaluated:
          w = base * (1 + alpha * (1 - GetConf(v)))      // multiplicative variant
          // additive variant:  w = base + beta * (1 - GetConf(v))
  run Dijkstra from this node
  for each reachable destination D:
      next hop = first node on the path to D
      install route (D, nextHop, outgoing interface, hops)

Since "who the destination is" changes whether v is penalised, the simplest implementation penalises every node entered and accepts a constant offset. The offset is the same for all paths to a given destination, except on the last hop, so choice of path is almost unaffected. Say this in the paper or exclude the destination as the prototype does.

Anti-flapping (do not skip)
  - Smoothing is already in the confidence model.
  - Add hysteresis: replace the current next hop only if the new path cost is lower by a margin (for example 10 percent), or if the current path became invalid.
  - Add a minimum time between route changes per destination.

Required test: with all confidences 1.0 and alpha > 0, routes must equal stock OLSR hop-count routes. Write this as a short scenario and compare routing tables on a fixed topology with PrintRoutingTableAllAt.

Debug scenario (build this first, before the big experiments)
  Diamond topology, 4 static nodes: S, A, B, D with S-A-D and S-B-D. Force A to c = 0.2 and B to c = 1.0. Expected: S routes to D through B. Then raise A to 1.0 and lower B: the route should move to A after the hysteresis margin. Draw this as a figure in the paper.

### Options if Stage 5C is too heavy
  - Ask your supervisor or lab for an existing ETX-enabled OLSR (olsrd-style) ns-3 implementation, and add only the confidence part.
  - Build on AODV instead: add confidence to RREQ and RREP, accumulate a path cost in the RREQ as it travels, and let the destination pick the lowest cost reply. Smaller change, less natural for proactive state.
  - Reduce scope for a first paper: report the Python prototype results plus one ns-3 validation scenario. Weaker, but honest, and extendable.

----------------------------------------------------------------------
## Stage 6: Experiments (about 2 weeks including debugging)

What to compare (series in every plot)
  1. olsr-hop                stock OLSR, hop count
  2. olsr-etx                if you built Option B
  3. uar-mult                 confidence-aware, multiplicative
  4. uar-add                  confidence-aware, additive
  5. uar-threshold           hard cutoff, as a baseline to beat

Parameter grid
  nNodes             20, 50, 100
  speed              0, 5, 15 m/s
  fragileFraction    0, 0.1, 0.25, 0.5
  alpha              1, 2, 4, 8
  update policy      periodic, event-triggered (delta = 0.05, 0.1, 0.2)
  runs               20 to 30 seeds per cell

Metrics to log (one CSV row per run)
  pdr, meanDelay, ctrlBytes, ctrlPkts, routeChanges,
  lowRelayShare, usefulDelivery

The two bespoke metrics need tracing, because FlowMonitor cannot see them
  lowRelayShare and usefulDelivery require knowing which relays each packet used. Easiest approach:
    - Hook the "forward" event in the routing protocol (where a node forwards a data packet; in ns-3 OLSR that is the route output/forward path), and record (packet uid, forwarding node id).
    - At the end, for each delivered packet, collect the relays it crossed.
    - lowRelayShare  = delivered packets that crossed a relay with c < 0.5 (c at the moment of forwarding), divided by delivered packets
    - usefulDelivery = average over delivered packets of the product of relay confidences at forwarding time (undelivered = 0)
  Use the same definitions as the Python prototype so the two can be compared.

Automation (bash, runs everything and appends to CSVs)
  for n in 20 50 100; do
   for f in 0 0.1 0.25 0.5; do
    for a in 1 2 4 8; do
     for run in $(seq 1 20); do
       ./ns3 run "uar-mesh --nNodes=$n --fragile=$f --alpha=$a --run=$run --outCsv=results.csv"
     done
    done
   done
  done

That is 3 x 4 x 4 x 20 = 960 runs. Each run is usually seconds to a few minutes. Start with a tiny grid, check the outputs look sane, then go big. Run in the background with nohup, or use several terminals.

Sanity checks before you trust any number
  - fragile = 0 and alpha = 0 must reproduce the stock OLSR numbers.
  - ctrlBytes should grow with nNodes.
  - Results should vary across runs; if all runs are identical, the seed is not changing.
  - Use the same seeds across protocols, so each seed is a paired comparison.

----------------------------------------------------------------------
## Stage 7: Analysis, plots, paper (about 2 to 3 weeks)

Aggregate in Python
  import pandas as pd, numpy as np
  df = pd.read_csv("results.csv")
  g = df.groupby(["proto", "fragile"])["usefulDelivery"]
  summary = g.agg(["mean", "std", "count"])
  summary["ci95"] = 1.96 * summary["std"] / np.sqrt(summary["count"])

Plots to make
  1. usefulDelivery vs fragile fraction, one line per protocol, with error bars   (headline figure)
  2. lowRelayShare vs fragile fraction
  3. ctrlBytes vs nNodes, periodic vs event-triggered
  4. meanDelay and PDR vs fragile fraction (the cost of avoidance)
  5. usefulDelivery vs alpha (sensitivity)
  6. routeChanges per minute with and without hysteresis
  7. The diamond-topology rerouting figure

Report negative results too: sparse networks, high alpha (long detours), high mobility where scores are stale.

Paper structure and section targets are in the roadmap from the earlier message. The mapping is:
  Section 4 (design)       Stage 5A to 5C
  Section 5 (overhead)     Stage 3 control bytes plus the formula from Stage 5A
  Section 6 (setup)        Stages 3, 4, 6
  Section 7 (results)      Stage 7

----------------------------------------------------------------------
## Overhead formulas to put in the paper

Let
  N        number of nodes
  H        HELLO interval (s)
  T        TC interval (s)
  b        added bytes per message (0 for the reserved-field variant, 1 to 4 for TLV)
  m        mean hop-count a TC message is flooded over (about the number of MPRs that retransmit)

Periodic policy, extra bytes per second across the network
  O_periodic = N * b * (1/H + m / T)

Event-triggered policy, with r = average confidence-change events per node per second
  O_event = N * b * (r * (1 + m))      bounded above by O_periodic

Relative overhead
  O_periodic / baseline control bytes per second, from your Stage 3 measurement

Fit your measured ctrlBytes against these. If they match, the analysis is validated.

----------------------------------------------------------------------
## Suggested schedule (12 to 14 weeks)

  Week 1        Stage 1 prototype, literature reading
  Week 2        Stages 2 and 3
  Week 3        Stage 4, start Stage 5 (rename and baseline equivalence)
  Weeks 4-6     Stage 5A to 5C, diamond test
  Week 7        Tracing for the two custom metrics
  Weeks 8-9     Stage 6 runs, fix bugs
  Weeks 10-11   Stage 7 plots, draft paper
  Weeks 12-13   Revise, add ETX or second experiment, supervisor feedback

If time is short, minimum viable version
  Python prototype results, Stage 5 with Option A (hop count) and the multiplicative cost, one mobility model, fragile fractions 0, 0.25, and 0.5, 20 seeds, and the diamond figure.

----------------------------------------------------------------------
## Common mistakes

  - Changing OLSR before the renamed copy reproduces stock results.
  - Using one seed and trusting it. Always use many seeds.
  - Comparing against a weak baseline. Include the threshold variant and ETX if you can.
  - Defining "useful delivery" after seeing results. Fix the definition first.
  - Letting confidence jump instantly. Smooth it and add hysteresis.
  - Claiming real-world benefit from a purely random confidence model. Say it is a model.
  - Forgetting backward compatibility: say what an old node does when it receives the new field (ignores it) and what a new node does when it hears none (default value).
