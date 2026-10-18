# Beginner Roadmap: Confidence-Aware Routing Project
Everything from "I understand nothing" to "I can present this to my teacher and write the paper".

How to use this file
  Read Part 1 and Part 2 first (about 20 minutes). Then do the steps in Part 4 in order. Every step has the same layout:
    What you do        the actual actions
    What it means      why this step exists, in plain words
    What you should see   how to know it worked
    If it goes wrong   the usual fixes
    Show your teacher  what to put on screen

Honesty note
  Steps 1 to 6 use the Python prototype and were really run (the numbers in Part 6 come from those runs).
  Steps 7 to 12 use ns-3, the real network simulator. Those files were written but could not be tested where they were produced, so expect small fixes. Step 10 (changing the routing software itself) is the hardest part of the whole project.

----------------------------------------------------------------------
## PART 1: The whole project as a story

The setting
  Imagine 50 students standing in a big field, each holding a phone. There are no phone towers. If student A wants to send a message to student Z far away, the message is passed from student to student until it arrives. Each student who passes it on is called a relay. A network like this, made of moving devices that pass messages for each other, is called a MANET (Mobile Ad hoc NETwork). Drones, cars and robots form MANETs.

The rule book students follow
  A rule book decides which students should pass a message along. That rule book is called a routing protocol. The one we study is called OLSR. Its normal rule is simple: choose the path that has the fewest passes, through connections that work well. It only cares about the connection (the radio signal) between students.

The problem
  Sometimes a student has a perfect connection but is not reliable. Maybe their battery is failing, their sensor is confused, or they keep dropping messages. The normal rule book cannot see this. It keeps sending messages through them, and messages get lost.

Our idea
  Give every student a score between 0 and 1 called confidence. It means "how reliable have I been recently?" 1 is perfect, 0 is hopeless. Students share their score with everyone. The rule book then says: prefer paths through students with high confidence, so low-confidence students become less attractive.

Two important twists
  1. The score changes over time (dynamic). A student who was reliable can become unreliable and can recover.
  2. We do not simply ban low-confidence students. Banning is easy but can force absurd detours. Instead we add a penalty to the path cost. If avoiding a bad student would mean a huge detour, the network may still use them. That is the trade-off.

The real question we study
  Making routes avoid unreliable students improves delivery, but it costs something: longer paths, slower delivery, more messages for sharing scores, and routes that flip around too often. So the project asks:
    Under what conditions is it worth it, and how can we get the benefit without paying too much?

Two tools we add to control the cost
  Adaptive weighting: how strongly we care about confidence changes with how bad the network is. If most students are fine, be relaxed. If many are unreliable, be strict.
  Hysteresis: do not change a route unless the new one is clearly better. This stops the network from flip-flopping between two almost equal routes.

What you will produce
  1. A working model of the idea (done: the Python prototype).
  2. Numbers and pictures showing benefit and cost (done in the prototype, to be repeated in the real simulator).
  3. A map showing when the idea is worth using and when normal OLSR is enough.
  4. A research paper.

Working title
  Confidence-Aware OLSR: Characterizing the Reliability-Routing-Cost Trade-off in Dynamic MANETs
  (Caution: the phrase "confidence-aware OLSR" already appears in two published papers. Mention them in your paper and explain how yours differs. See LITERATURE_REVIEW.md. A title with less overlap: "Reliability-Cost Trade-offs of Dynamic Node-Confidence Routing in OLSR-Based MANETs".)

----------------------------------------------------------------------
## PART 2: Words you will hear (plain-language dictionary)

node                a device in the network (one student, one drone)
link                the radio connection between two nodes
hop                 one pass from one node to the next. A path with 3 passes has 3 hops
hop count           how many hops a path has. Fewer is usually better
route / path        the chain of nodes a message travels through
relay               a node in the middle of a path that passes the message on
packet              one small chunk of data. A message is many packets
routing protocol    the rule book that picks routes (AODV, DSR, OLSR are examples)
OLSR                a routing protocol where every node regularly tells the others who its neighbours are, so everyone can compute the best routes in advance
ETX                 a number saying how many tries it takes on average to get a packet across a link. 1 is perfect, bigger is worse
PDR                 packet delivery ratio: out of 100 packets sent, how many arrived. 0.8 means 80
delay               how long a packet takes to arrive
overhead            extra messages the network sends just to organize itself (not your actual data). Our confidence scores add a little overhead
route change        the moment a node switches from one path to another
route flapping      switching back and forth between routes again and again, which wastes effort and drops packets
confidence          our 0 to 1 reliability score for a node
EMA                 exponential moving average. A way to update a score smoothly: new score = 80% old score + 20% latest result. It prevents wild jumps
alpha (the Greek letter a)   a dial that says how much we care about confidence. alpha = 0 ignores confidence (normal OLSR). A big alpha avoids low-confidence nodes strongly
penalty             extra cost added to a path, so the router finds it less attractive
cost                a number the router tries to minimize when it picks a path
hysteresis (H)      a margin. Switch routes only if the new one is cheaper by more than H (for example 10 percent)
baseline            the normal version you compare against (plain OLSR)
simulation          a computer experiment that imitates the network instead of building real hardware
ns-3                a well-known network simulator used by researchers
seed                a number that fixes the randomness of one simulation run. Different seeds give different random scenarios. Researchers run many seeds so results are not a fluke
95 percent confidence interval   the "plus or minus" range around an average. A narrow range means the average is trustworthy. (Do not mix this up with our node confidence score, which is a different thing.)
Pareto frontier    the set of options where you cannot improve one thing (reliability) without making another (delay) worse. It shows the best trade-offs
fault injection     deliberately making some simulated nodes unreliable so we can test the idea
CSV                 a plain table file you can open in Excel

----------------------------------------------------------------------
## PART 3: The map of steps

| Step | What | Why | Rough time |
|------|------|-----|-----------|
| 0 | Prepare your computer | You need Python and a folder | 30 min |
| 1 | Understand the idea with one picture | You must be able to explain it | 1 hour |
| 2 | Run the flapping demo | Shows why hysteresis exists, in 10 seconds | 10 min |
| 3 | Run the main prototype | Shows the benefit and the cost with numbers | 30 min |
| 4 | Read the alpha sweep | Finds the "sweet spot" for the dial | 30 min |
| 5 | Run the decision map | Shows when the idea is worth using | 30 min |
| 6 | Play with the settings | Builds your understanding | 1 to 2 days |
| 7 | Install ns-3 | The real simulator | half a day |
| 8 | Run normal OLSR in ns-3 | Your comparison point | 1 day |
| 9 | Add the confidence generator | Give simulated nodes a score | 1 day |
| 10 | Change OLSR itself | The actual research implementation | 2 to 4 weeks |
| 11 | Diamond test | Proves the change works | 2 days |
| 12 | Run all experiments | Collect the evidence | 1 to 2 weeks |
| 13 | Analyze results | Turn raw numbers into pictures | 3 days |
| 14 | Check the literature | Avoid claiming what others already did | ongoing |
| 15 | Write the paper | The deliverable | 2 to 3 weeks |
| 16 | Present to your teacher | Explain with demos | 1 day to prepare |

You can show your teacher meaningful progress after Step 5, before touching ns-3 at all.

----------------------------------------------------------------------
## PART 4: The steps in detail

### Step 0: Prepare your computer

What you do
  1. Use Linux (Ubuntu), or Windows with WSL2 (a Linux inside Windows), or a Mac. The Python parts work on any of them. ns-3 later works best on Linux.
  2. Open a terminal (the text window where you type commands).
  3. Check Python:
       python3 --version
     It should say 3.8 or newer.
  4. Install the plotting library (needed only for pictures):
       pip install matplotlib
  5. Put the project folder somewhere easy, then go into it:
       cd uar-mesh
       ls

What it means
  Python runs your prototype. The prototype is a quick sketch of the idea that runs in seconds, so you can learn and experiment before the heavy simulator.

What you should see
  The ls command lists: IMPLEMENTATION_GUIDE.md, RESEARCH_PLAN_V2.md, LITERATURE_REVIEW.md, this file, and folders prototype, ns3, analysis.

If it goes wrong
  "python3: command not found": install Python from python.org.
  "pip: command not found": try python3 -m pip install matplotlib.

### Step 1: Understand the idea with one picture

What you do
  On paper, draw this "diamond":

          A  (confidence 0.2, unreliable)
        /   \
   S ---     --- D        S = sender, D = destination
        \   /
          B  (confidence 0.9, reliable)

  Both routes S-A-D and S-B-D have 2 hops, so normal OLSR sees them as equal and may pick A. Confidence-aware OLSR sees that A is unreliable and picks B.
  Now change it: suppose avoiding A needs a 6-hop detour. Then you decide whether the detour is worth it. That decision is the whole research question.

What it means
  This one picture is the entire project. Everything else is measuring it carefully.

What you should be able to say afterwards
  "Normal routing only looks at connections. We also look at how reliable each node has been, and we study how much it is worth paying to avoid unreliable nodes."

Show your teacher
  The diamond drawing.

### Step 2: Run the flapping demo (the smallest demonstration)

What you do
  cd prototype
  python3 flapping_demo.py --plot flapping.png

What it means
  Two routes are almost equally good, and their scores keep crossing by tiny amounts. Without a margin, the router switches every time they cross. This script counts the switches for different margins H.

What you should see (these are the real numbers from the run)
  H = 0     17 switches in 120 seconds
  H = 0.02   9
  H = 0.05   2
  H = 0.10   0
  H = 0.15   0
  and a picture flapping.png: top graph shows the two scores crossing, the two lower graphs show which route is used with and without the margin.

If it goes wrong
  "No module named matplotlib": run the pip install from Step 0. Without --plot it still prints the numbers.

Show your teacher
  The picture, and one sentence: "Without hysteresis the network keeps flip-flopping. With a 10 percent margin it stays put."

### Step 3: Run the main prototype

What you do
  python3 uar_dynamic.py --trials 30 --base etx --fragile 0.25 --speed 5 --csv results.csv --plot figs
  (It takes about 1.5 minutes.)

What it means
  This simulates 50 moving nodes for 5 minutes. A quarter of the nodes are "fragile": they randomly become unreliable and later recover, and while unreliable they really drop packets. Every node measures its own forwarding success and updates its confidence with the smooth update rule. Routes are recomputed every 5 seconds. Then the script compares normal routing against many confidence-aware versions, using the same 30 random scenarios for each, so the comparison is fair.

How to read the table (each column)
  config       which version: olsr is normal; add / mult / threshold are different ways of adding the penalty; (a=8,H=0.1) means alpha 8 and hysteresis margin 10 percent
  PDR          fraction of packets delivered. Higher is better
  +-           the plus-or-minus range around that average
  dPDR%        improvement over normal routing in percent
  hops, dHop%  average path length and its change
  delay, dDel% delay (an estimate in milliseconds) and its change
  chg/min      route changes per flow per minute (stability; lower is calmer)
  low%         share of packets that travelled through a really unreliable node
  ovh_ev%      estimated extra control traffic if scores are sent only when they change
  flags        A means it meets your acceptability limits; P means it is on the Pareto frontier (a best-trade-off point)

What you should see (real numbers from the run)
  olsr              PDR 0.673, 31.4% of packets crossed a bad node, 5.05 route changes/min
  add(a=8,H=0)      PDR 0.817 (21 percent better), delay 9 percent higher, bad-node share 7.2%
  There is also a check at the top saying that with alpha = 0 the confidence version reproduces normal routing exactly. That check protects you from silent bugs.

Show your teacher
  The table (top 5 rows plus olsr) and the picture figs/pareto_pdr_vs_delay.png. Explain: "Each dot is one setting. Higher means more reliable, further left means faster. Stars are the best trade-offs."

### Step 4: Read the alpha sweep (the sweet-spot question)

What you do
  Look at the bottom of the Step 3 output (the section "Alpha sweep") and open figs/alpha_sweep.png.

What it means
  Alpha is the dial for "how much do we care about confidence". Turn it from 0 up to 16 and watch what happens. The question: where do extra turns of the dial stop paying off?

What you should see (real numbers)
  alpha 0    no change from normal routing
  alpha 1    PDR +11.5 percent, delay +4.6
  alpha 2    +16.0, delay +6.3
  alpha 4    +19.4, delay +7.8
  alpha 8    +21.3, delay +9.2   (the program marks this as the knee, the point of diminishing returns)
  alpha 16   +21.6, delay +10.2
  Going from 8 to 16 gains almost nothing in reliability but costs more delay.

Why this matters
  It is the "useful operating region" result: moderate alpha gives most of the benefit. In the paper this becomes a finding, but only after you repeat it in ns-3. In the prototype it is a model result.

Show your teacher
  The alpha_sweep.png picture.

### Step 5: Run the decision map (when is it worth using?)

What you do
  python3 uar_boundary.py --trials 15 --base etx --alpha 8 --H 0.1 --csv boundary.csv --plot figs_boundary
  (About 3 minutes. Open figs_boundary/decision_map.png.)

What it means
  The map tries many situations: nodes standing still, walking, and moving fast, combined with 0, 10, 25 and 50 percent unreliable nodes. For each situation the script decides one label using rules that were fixed in advance:
    OLSR sufficient    normal routing is good enough (our version gives no real gain)
    beneficial         real gain at acceptable cost and stable routes
    needs hysteresis   real gain, but route flip-flopping appears unless the margin is used
    too costly         real gain, but delay or path length goes beyond the allowed limit
    unstable           flip-flopping remains even with the margin

What you should see (real numbers, 15 seeds per cell)
  0 percent unreliable nodes: OLSR sufficient at every speed (confidence gives nothing, slightly negative)
  10 and 25 percent unreliable, nodes moving: beneficial (gains of 8 to 20 percent)
  10 and 25 percent unreliable, nodes standing still: needs hysteresis
  50 percent unreliable: too costly in every case (large gains of 37 to 43 percent, but delay rises 13 to 17 percent, past the placeholder limit of 10)

Be careful about these three things
  1. The limits (10 percent delay, 15 percent hops, 5 percent gain) are placeholders. You must justify real ones before running the final experiments.
  2. A first run exposed a flaw: a standing network has zero route changes for normal routing, so every change looked "unstable". I added an absolute allowance of 1 route change per flow per minute and reran. That was a rule fix, not a tuning to flatter the result, but you must state it in the paper as a design choice.
  3. This is a model, not the real world.

Show your teacher
  The decision map picture. It is the most "research-like" figure you have.

### Step 6: Play with the settings (build understanding)

What you do
  Run these one at a time and compare. Each is a question you can answer yourself.
  Question: does the idea matter when conditions are bad?
    python3 uar_dynamic.py --trials 20 --base etx --fragile 0.5
  Question: what if nodes move fast?
    python3 uar_dynamic.py --trials 20 --base etx --speed 15
  Question: what if reliability changes twice as fast?
    python3 uar_dynamic.py --trials 20 --base etx --volatility 2
  Question: does it matter if score updates are slow or fast? (higher lam = slower)
    python3 uar_dynamic.py --trials 20 --base etx --lam 0.95
  Question: what if an avoided node never gets a second chance?
    python3 uar_dynamic.py --trials 20 --base etx --recovery 0
  Question: do hysteresis margins matter?
    python3 uar_dynamic.py --trials 20 --base etx --hyst 0 0.05 0.1 0.15

What it means
  Each setting is a knob. Understanding which knobs matter is what separates "I ran a program" from "I understand the research".

Things to notice
  - Compare each hysteresis row against the olsr(H=...) rows, not only against plain olsr. In my run, a margin of 0.1 also made plain routing calmer (5.05 to 2.98 changes per minute). So hysteresis helps stability in general. What is specific to confidence is that confidence-aware routing changes routes somewhat more than plain routing even with the margin (3.51 versus 2.98).
  - With --recovery 0, avoided nodes may never regain confidence. That is the "no second chance" problem and it is a good thing to explain.
  - With base hop count, "add" and "mult" give identical results (the maths makes them the same). To tell them apart you need ETX as the base.

### Step 7: Install ns-3 (the real simulator)

What you do
  Use Linux. Then:
    sudo apt update
    sudo apt install g++ python3 cmake ninja-build git ccache make
    wget https://www.nsnam.org/releases/ns-allinone-3.40.tar.bz2
    tar xjf ns-allinone-3.40.tar.bz2
    cd ns-allinone-3.40/ns-3.40
    ./ns3 configure --enable-examples --enable-tests
    ./ns3 build
  The build takes 20 to 60 minutes. Check it works:
    ./ns3 run first
  (3.40 is an example. A newer release from nsnam.org is fine, with the same steps.)

What it means
  The prototype is a sketch. ns-3 simulates real radio behaviour, real message formats and real protocol code. Reviewers trust ns-3 results far more than a home-made sketch, so the paper's numbers must come from here.

What you should see
  The command prints a short message from the first example and no errors.

If it goes wrong
  Missing packages: read the error, install what it names with apt.
  Very slow: it is normal the first time.

### Step 8: Run normal OLSR in ns-3 (your comparison point)

What you do
  Copy the baseline script in and run it:
    cp <path>/uar-mesh/ns3/uar-baseline.cc scratch/
    ./ns3 run "uar-baseline --proto=olsr --nNodes=30 --speed=5 --run=1"
  Then run it for 20 different seeds:
    for run in $(seq 1 20); do
      ./ns3 run "uar-baseline --proto=olsr --nNodes=30 --run=$run --outCsv=olsr_base.csv"
    done

What it means
  Before changing anything you must know how normal OLSR behaves. Every later claim is "better or worse than this".

What you should see
  One line per run: PDR, delay, and control bytes. A file olsr_base.csv grows with one row per run.

If it goes wrong
  PDR 0: nodes are too far apart for the default radio. Shrink the area: --area=200, or raise power: --txPower=20.
  Compile errors: ns-3 versions differ slightly. Read the first error; usually one function name changed.

### Step 9: Add the confidence generator and the dropping nodes

What you do
  Copy ns3/uar-confidence-manager.h into scratch/. In a copy of the baseline script (call it uar-mesh.cc):
    #include "uar-confidence-manager.h"
    ... after creating nodes:
    UarConfidenceManager::Install(nNodes, 0.25);
  Meaning: 25 percent of nodes will randomly become unreliable and recover.

What it means
  Simulated nodes have no real sensors. This helper does two jobs: it secretly decides when each fragile node is truly unreliable and makes it drop a share of packets (so delivery really suffers), and it computes the confidence score each node would announce, using the smooth update rule.

What you should see
  Print each node's score every 10 seconds: fragile nodes dip and recover slowly, healthy ones stay near 1.

### Step 10: Change OLSR itself (the hardest step)

Do not try this in one go. Break it into mini-steps and test after each.

10a. Make a private copy of OLSR
  In the ns-3 source folder, copy the olsr folder to uar-olsr and rename it. Build it and run the baseline using your copy. Result must be identical to stock OLSR for the same seed.
  Meaning: you prove your copy is a faithful twin before changing anything.

10b. Put the score into the messages
  OLSR already has unused spare bits in its HELLO and TC messages. Use 8 of them for the confidence score. This adds zero extra bytes. (Detailed bit layout and code snippets: IMPLEMENTATION_GUIDE.md, Stage 5A.)
  Meaning: HELLO and TC are the "announcements" nodes send regularly. We attach the score to them.

10c. Remember what others announced
  Each node keeps a small table: node name and its latest announced confidence and when it was heard. If a score is old or unknown, use a default and decide on purpose whether the default is optimistic (1.0) or pessimistic.

10d. Use the score in the route cost
  Replace the route-building step with the "cheapest path" calculation, where entering a node costs 1 plus alpha times (1 minus its confidence). (Pseudo-code: IMPLEMENTATION_GUIDE.md, Stage 5C.)
  Meaning: this is the actual idea turned into code.

10e. Add the margin (hysteresis)
  Keep the current route unless the new one is cheaper by more than H.

10f. Add the packet dropping for unreliable nodes
  Where a node forwards a packet that is passing through, ask the helper whether to drop it:
    if (UarConfidenceManager::ShouldDrop(nodeId)) { drop it; return; }
  Meaning: without this, unreliable nodes would still forward everything and delivery could not change.

10g. Add the adaptive weighting
  alpha = alpha_low + (alpha_high - alpha_low) * (fraction of nodes that currently look unreliable, capped at 1) / (a reference fraction).
  Meaning: strict when many nodes look bad, relaxed when few do.

If this step is too heavy
  Options in the guide: ask your supervisor for an existing OLSR with ETX; build on AODV instead; or present the prototype results plus one ns-3 validation scenario for a smaller first paper.

### Step 11: The diamond test (is the change really working?)

What you do
  Copy ns3/uar-diamond.cc into scratch/ and run:
    ./ns3 run "uar-diamond"
  It builds the A and B diamond from Step 1, makes A unreliable and B reliable, and prints the sender's routing table at 40 seconds. At 60 seconds it swaps their reliability and prints again at 100 seconds.

What it means
  This is the smallest possible proof. If the route goes through B first and then moves to A, the idea works. If not, stop and fix before running any big experiment.

What you should see
  Plain OLSR: the route ignores the scores. Your version: first via B (10.1.0.3), later via A (10.1.0.2), and not flipping on tiny changes.

### Step 12: Run the full experiments in ns-3

What you do
  Use the experiment table (these match what the prototype already explored):
    number of nodes: 20, 50, 100
    speed: 0, 5, 15 m/s
    fraction of unreliable nodes: 0, 10, 25, 50 percent
    alpha: 0, 1, 2, 4, 8, 16
    hysteresis: 0, 5, 10, 15 percent
    seeds: 30 per setting
  Always compare against the fair baselines: plain OLSR, and plain OLSR with the same hysteresis.
  Decide the acceptability limits and write them down before you run (Part 5 explains them).

What it means
  One run proves nothing. Thirty runs per setting turn a lucky result into evidence.

What you should see
  A growing results.csv: one row per run with PDR, delay, control bytes, route changes, and bad-node share.

Tip
  Start with 3 seeds and a tiny grid to catch mistakes, then scale up. Use a script with nested loops (example in IMPLEMENTATION_GUIDE.md, Stage 6) and run it in the background.

### Step 13: Analyze the results

What you do
  python3 analysis/analyze_results.py results.csv
  (Use --demo first to see what the outputs look like on fake data.)

What it means
  The script averages across seeds, computes plus-or-minus ranges, and draws the pictures the paper needs. It also compares each version with the baseline seed by seed.

What you should see
  A figures folder with the plots and summary CSV files.

Be honest
  Report cases where the idea does not help. Those boundaries are part of your contribution.

### Step 14: Check the literature (do this in parallel, all along)

What you do
  Follow the to-do list in LITERATURE_REVIEW.md: read the full texts of the closest papers (TCAOLSR, OLSRT-C, TUE-OLSR, and the ns-3 trust OLSR paper), run the search strings on Google Scholar and IEEE Xplore, and look at papers that cite them.

What it means
  Reviewers reject papers that claim to be new when they are not. A careful related-work section protects you. Write "our literature review did not identify..." instead of "no one has ever...".

### Step 15: Write the paper

Order that makes it easiest
  1. Method section (you already have the formulas)
  2. Setup section (parameters table)
  3. Results (one subsection per research question)
  4. Introduction and related work
  5. Abstract and conclusion last
Use RESEARCH_PLAN_V2.md, Section 9, for the full outline.

Your contribution list (state it plainly)
  1. A dynamic node-confidence estimate used inside OLSR route cost.
  2. A soft penalty (not a ban), tested in additive, multiplicative and threshold forms.
  3. Adaptive confidence weighting based on network conditions.
  4. Route-level hysteresis to control the flip-flopping that dynamic confidence can cause.
  5. A systematic characterization of the reliability versus delay, path length, overhead and stability trade-off across density, mobility, unreliable-node fraction, confidence volatility, alpha and hysteresis, ending in a map of when it is worth using.
  Do not claim that adding confidence or trust to OLSR is new. Several papers already do that.

### Step 16: Present to your teacher

See Part 5.

----------------------------------------------------------------------
## PART 5: Presenting to your teacher

Two-minute explanation (say it in your own words)
  "In networks of moving devices like drones, messages pass through other devices. Normal routing picks paths by how good the radio connection is, but a device with a good connection can still be unreliable. We give each device a reliability score that updates over time, and we make the routing avoid unreliable devices, but only when the benefit is worth the cost. Our research question is: under what conditions is that worth it, and how do we get the benefit without making routes slow, long or unstable? We built a quick model to test the idea, and next we repeat the experiments in a standard network simulator."

Ten-minute demo order
  1. The diamond drawing (1 minute). The idea in one picture.
  2. flapping.png (1 minute). Why we need a margin.
  3. Main table, top rows (2 minutes). Normal 0.673 delivery, confidence version 0.817, delay up about 9 percent, packets through bad nodes down from 31 percent to 7 percent.
  4. alpha_sweep.png (2 minutes). The dial: big gains early, almost nothing after alpha 8.
  5. decision_map.png (2 minutes). Normal OLSR is enough when everyone is reliable. Confidence helps with 10 to 25 percent unreliable nodes. With half the nodes unreliable, gain is large but cost exceeds our limit.
  6. The plan (2 minutes). Show the step table from Part 3: what is done (model) and what is next (ns-3).

What you can say is already done and what is not
  Done: the idea, a working model, a fair comparison method, first results, a literature check.
  Not done: the real-simulator implementation, real overhead measurements, full statistics at scale, the paper.

Questions your teacher may ask, with honest answers
  Q: Is this new? Trust-based OLSR already exists.
  A: Yes, trust and confidence in OLSR exist (two papers even use the word confidence). We do not claim the basic idea is new. Our contribution is to measure the reliability versus cost trade-off, to control instability with hysteresis, to adapt the weighting, and to map when it is worth using. We are still verifying this against full texts of the closest papers.

  Q: Are your results real?
  A: They come from our own model, where we decided how unreliable nodes behave. They justify building the ns-3 version. The paper's numbers will come from ns-3.

  Q: Why not just ban unreliable nodes?
  A: A ban can disconnect parts of the network or force huge detours. We tested a threshold version too, and a soft penalty keeps options open.

  Q: What does hysteresis do, and is it your invention?
  A: It stops route flip-flopping. No, hysteresis itself already exists in OLSR for links. Ours acts on route cost when confidence changes. Also, in our test the margin calmed plain routing too, so we compare against plain routing with the same margin.

  Q: What are the limits you chose for "acceptable" cost?
  A: Currently 5 percent gain, 10 percent delay, 15 percent path length and 10 percent overhead, as placeholders. We will justify and fix them before the final experiments, and also show the full trade-off curve so the conclusion does not depend on one number.

  Q: How is confidence measured in real life?
  A: In the model, each node counts its own forwarding successes. In reality it could come from neighbours overhearing whether a packet was forwarded, or from a node's own estimator such as a position filter. We plan to support both.

  Q: What about nodes lying about their confidence?
  A: We assume honest reporting. Lying nodes are future work.

  Q: Overhead?
  A: Our estimate says about 2.4 percent extra control traffic with a 2-byte field, and zero extra bytes if the field uses spare bits. That is an estimate from assumed message sizes; ns-3 will measure it.

----------------------------------------------------------------------
## PART 6: What the prototype found (and what it does not prove)

Setting: 50 nodes, 25 percent fragile, speed up to 5 m/s, ETX base, 30 seeds, 300 seconds.

  Normal routing: PDR 0.673, bad-node share 31.4 percent, 5.05 route changes per minute
  Alpha 1, 2, 4, 8, 16 (additive, no margin): PDR +11.5, +16.0, +19.4, +21.3, +21.6 percent; delay +4.6, +6.3, +7.8, +9.2, +10.2 percent
  Knee of the curve: alpha 8
  Margin 0.1: route changes 5.46 to 3.51 for alpha 8, and 5.05 to 2.98 for plain routing (so the margin helps both)
  Adaptive alpha (no margin): +15.9 percent, less than a well-chosen fixed alpha of 8 (+21.3). Report this honestly.
  Estimated extra control traffic: 2.4 percent if periodic, with assumed message sizes

Decision map (alpha 8, margin 0.1, 15 seeds): see Step 5.

What this does not prove
  - Unreliable nodes drop packets in the way we defined
  - Delay is an estimate (tries times 5 ms plus 2 ms per hop), counted for delivered packets only
  - Overhead is a calculation, not a measurement
  - Confidence comes from each node watching its own forwarding, no neighbour checking, no liars
  - The acceptability limits are placeholders
  These numbers say "worth building the real version". They are not the paper's evidence.

----------------------------------------------------------------------
## PART 7: Common problems and what they mean

  The numbers differ slightly each time I run    The seeds are fixed, so results should repeat exactly. If they do not, you changed a setting.
  A confidence version is not better than normal  That is allowed and informative. With no unreliable nodes (0 percent) the idea should give nothing.
  Plots do not appear                              Install matplotlib, and pass --plot FOLDER.
  ns-3 PDR is zero                                 Nodes cannot hear each other. Shrink the area or raise the power.
  Routes flip constantly                           Increase the hysteresis margin or the smoothing (lam).
  An avoided node never recovers                   Raise --recovery above 0 (this is the second-chance mechanism).
  My teacher says "this exists already"            Agree where true, then point to the trade-off, stability and decision-map parts, and to LITERATURE_REVIEW.md.

----------------------------------------------------------------------
## PART 8: Checklist

  [ ] Step 0 set up
  [ ] Can draw and explain the diamond
  [ ] Ran the flapping demo and saved the picture
  [ ] Ran the main prototype and can read every column
  [ ] Can explain the alpha dial and the knee
  [ ] Ran the decision map and can explain each label
  [ ] Chose and justified the acceptability limits before final runs
  [ ] ns-3 installed and baseline run for 20 seeds
  [ ] Confidence generator added to the ns-3 scenario
  [ ] OLSR copy reproduces stock OLSR exactly
  [ ] Confidence in packets, table, cost, margin, dropping, adaptive weighting
  [ ] Diamond test passes
  [ ] 30 seeds per setting on the full grid
  [ ] Plots and tables generated
  [ ] Full texts of closest papers read, gaps verified
  [ ] Paper drafted, limitations written honestly
