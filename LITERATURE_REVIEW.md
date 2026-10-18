# Literature check: confidence / trust-aware OLSR
Prepared 8 October 2026 for the project "Confidence-Aware OLSR: Exploring the Reliability-Routing-Cost Trade-off in Dynamic MANETs".

----------------------------------------------------------------------
## 0. Scope and limits (read first)

What this is
  A first-pass search: 9 web searches, read at abstract or snippet level.
  Good enough to find the closest prior work and to decide what NOT to claim.

What this is not
  - Not a systematic review. No IEEE Xplore, ACM DL, Scopus or Google Scholar queries were possible.
  - Almost nothing was read in full text. Statements about what a paper "does not study" are statements about its abstract, not its body. Verify each before you cite it as a gap.
  - Some author lists and years were not visible in the search results and are marked "verify".

----------------------------------------------------------------------
## 1. Main finding

1. The phrase "confidence-aware OLSR" is already in use. Two papers (TCAOLSR and OLSRT-C) use trust together with node confidence values inside OLSR. They are framed around attacks (black hole, selfish behaviour), not around a reliability-cost trade-off.
2. Trust-based OLSR is a crowded area: at least six distinct OLSR trust protocols turned up in a handful of searches.
3. Combining hop count and trust in route selection is not new (TUE-OLSR does this explicitly).
4. Letting an avoided or isolated node regain standing is not new (reputation fading in CONFIDANT; redemption in later schemes).
5. Link-level hysteresis and ETX with hysteresis already exist in OLSR itself (OLSRd). Your hysteresis is route-level and confidence-driven; you must state that difference clearly.
6. I did not find, in these searches, work that (a) routes inside OLSR using a confidence score derived from the node's own state estimator, or (b) characterizes a reliability versus delay/hops/overhead/stability trade-off for confidence-aware OLSR with defined acceptability limits. Absence in a quick search is not proof of absence.

----------------------------------------------------------------------
## 2. Comparison table

Columns: what the per-node score is, where it comes from, how routing uses it, what was evaluated, and overlap with this project.

| # | Work | Protocol | Score / source | How routing uses it | Evaluated / fault model | Overlap |
|---|------|----------|----------------|---------------------|--------------------------|---------|
| A | TCAOLSR, "Random Black Hole Attack Modelling and Mitigation Using Trust-Confidence Aware OLSR", Int. J. Sensors, Wireless Comm. and Control 10(2), 2020 (authors: verify) | OLSR | Trust plus confidence, computed from observed behaviour | Trust-confidence aware route strategy | PDR, routing overhead, energy; random black hole attacks; reports PDR 40-60% better than OLSR in the mixed case | High on name and goal. Attack focus; abstract does not mention delay, hop count, hysteresis or alpha sweeps |
| B | OLSRT-C, Adoni, Tavildar, Warhade, "Modeling of Random Selfish Behavior Attack...", IJSWCC 11(4), 2021 | OLSR | Trust levels from a probabilistic ON/OFF attack model, plus node confidence values | Chooses forwarding path using trust and confidence | PDR, routing overhead, energy; selfish nodes 10% to 50% | High on name. Attack focus |
| C | TUE-OLSR, Wang, Zhang, Du, Qi, IEEE Access 8, 2020 | OLSR | Trust from cloud-model and fuzzy Petri net reasoning over performance metrics | Minimum trust-entropy route; combines hop count and trust | PDR and average latency against other trust-based OLSR protocols | Medium-high: hop count plus trust in one route choice |
| D | Lim, Lim, Ko, "Reliable Mutual Node Evaluation for Trust-Based OLSR in Tactical MANETs", QShine 2017 | OLSR | Trust from observed packet-forwarding capability | Trust used in MPR selection; updated by cross-layer delivery evidence | ns-3 simulation; attackers | Medium: forwarding-success-based trust in ns-3 OLSR |
| E | "Trust aware cooperative optimised link state routing protocol" (BT-OLSR), 2017 (authors: verify) | OLSR | Consolidated trust value from direct and indirect observations | Isolates misbehaving nodes from routes | Mobility 20 m/s, 50% malicious nodes | Medium |
| F | S-OLSR, Ren, Li, Hu, "An Improved Security OLSR Protocol against Black Hole Attack based on FANET" | OLSR | Fuzzy-logic trust value | Modifies MPR selection | ns-2.35; PDR, throughput, delay | Medium: UAV/FANET setting |
| G | Saddiki, Boukli Hacene, Gilg, Lorenz, "Trust-Neighbors-Based to Mitigate the Cooperative Black Hole Attack in OLSR", Springer 2019 | OLSR | Neighbour trust | Black-hole mitigation | Cooperative black hole | Low-medium |
| H | Alattar and Sailhan, "Reliable Trust Estimation in ad hoc Networks using Confidence Interval" (year: verify) | OLSR (as example) | Statistical confidence interval around a trust estimate | Decision making under trust uncertainty | Link spoofing and drop attacks | Low: "confidence" means statistical certainty of the trust estimate, not node state quality |
| I | Xia, Jia, Ju, Li, Sha, "Impact of trust model on on-demand multi-path routing", Computer Communications 36, 2013 | AOMDV | Trust prediction from history and fuzzy rules | Trusted multipath routing (AOTMDV) | PDR, throughput, attack resistance | Low: different protocol, confirms trust prediction is established |
| J | CONFIDANT, Buchegger and Le Boudec (EPFL) | DSR | Reputation and trust ratings | Isolates misbehaving nodes | Up to half the nodes misbehaving | Reputation fading allows redemption: prior art for your recovery term |
| K | Watchdog and Pathrater (as described in surveys) | DSR | Watchdog listens to the next hop | Pathrater routes around misbehaving nodes | Routing misbehaviour | Prior art for observation-based forwarding scores |
| L | Co-Agent, Chang, Li, Tang, Ad Hoc and Sensor Wireless Networks 33, 2016 | DSR and AODV | Reputation | Detect and avoid selfish nodes; misjudged nodes can redeem reputation | Selfish nodes | Prior art for redemption |
| M | OLSRd link quality (ETX) extension, with hysteresis in etx_ff | OLSR (olsrd) | Link quality, not node state | Smallest sum of link costs | Deployed in mesh networks | Prior art for ETX in OLSR and for link-level hysteresis |
| N | Johnson and Hancke, "Comparison of two routing metrics in OLSR on a grid based mesh network", Ad Hoc Networks (2008/2009, verify) | OLSR | Hysteresis metric versus ETX | Route selection | Testbed; hop count, overhead, delay, loss, route flapping | Useful precedent for measuring route flapping; found ETX performed worse than the simpler hysteresis metric in their grid |
| O | "Speed-Aware Routing for UAV Ad-Hoc Networks" (arXiv 1307.6350; authors: verify) | OLSRd | Speed-weighted ETX; position shared in Hello messages | ETX adjusted by node speed | UAV mobility | Closest "node state in the OLSR metric" I found; state is speed, not estimator confidence |
| P | CEL-OLSR, Jin, Zhang, Liu, Wang, Zhang, Sensors 24(5), 2024 | OLSR | Node mobility and load features, weighted by entropy and TOPSIS | MPR selection | ns-3; PDR, delay, throughput, overhead | Low-medium: shows ns-3 OLSR modifications with the same metric set |
| Q | Kwon and Shroff, "Geographic routing in the presence of location errors" (MER) | Geographic | Statistics of location error | Maximizes an expectation including location error | Mobile scenarios | Position uncertainty used in routing, not in OLSR |
| R | Milocco, Costantini, Boumerdassi, "Improved geographic routing in sensor networks subjected to localization errors", Ad Hoc Networks 13, 2014 | Geographic | Relay location uncertainty | Cost function over relay choice | Sensor networks | Same family as Q |
| S | Lim, Greenhalgh, Chesterfield, Crowcroft, "Hybrid routing: mitigating position uncertainty in geo-routing", UCAM-CL-TR-629, 2005 | Hybrid geographic plus topological | Position inaccuracy | Combines position and topology state | Up to 200 m position error | Same family as Q |
| T | Sawwan and Wu, "Age of information utility-based routing in networks with unreliable links" (Elsevier, 2026; confirm journal) | Utility-based | Freshness utility plus link reliability | Optimal path maximizing expected utility | Unreliable multi-hop links | Adjacent: routes by information value, not node state confidence |
| U | Greedy Kalman-Swarm (arXiv 2604.16868); Khodayi-mehr et al., "Distributed State Estimation Using Intermittently Connected Robot Networks" (arXiv 1805.01574) | n/a | Estimator covariance | Communication used to improve estimation | Robot swarms | Opposite direction: networking serves estimation. Useful for motivation, not as competitors |

----------------------------------------------------------------------
## 3. What each cluster means for your claims

Cluster 1: trust and confidence inside OLSR (A to G)
  Established: trust or confidence values computed from observed behaviour; used to avoid bad nodes; improved PDR under attack; some report overhead.
  Consequence: do not claim "confidence-aware OLSR" or "observation-based dynamic confidence" as new. The name collides with TCAOLSR and OLSRT-C, so cite both and explain how yours differs (fault model rather than adversary, trade-off characterization, hysteresis).
  Read in full: A, B and C. Check whether they report delay, hop count, route changes, parameter sweeps or acceptability limits. If they already do, the trade-off angle weakens.

Cluster 2: reputation systems (J to L)
  Established: watchdog observation, reputation, fading and redemption.
  Consequence: your recovery term is a version of reputation fading. Say so and cite it. Your angle is studying its effect on stability inside a proactive protocol with route-level hysteresis, not inventing recovery.

Cluster 3: link quality and hysteresis in OLSR (M, N)
  Established: ETX in OLSR, link-level hysteresis, measurements of route flapping.
  Consequence: your hysteresis must be described as route-cost hysteresis driven by changing node confidence, distinct from link hysteresis. Prior flapping measurements (N) give you a method to borrow.

Cluster 4: node state in an OLSR metric (O, P)
  Established: modifying OLSR metrics or MPR selection with node attributes (speed, mobility, load), evaluated in ns-3 with PDR, delay, throughput and overhead.
  Consequence: an "OLSR plus node attribute" paper is a recognized genre. The attribute you use (estimator-derived confidence) is the difference, so the estimator-agnostic framing matters.

Cluster 5: position and information uncertainty in routing (Q to T)
  Established: routing that accounts for position error or information freshness.
  Consequence: supports the motivation that routing should know about state quality. None of these, in the abstracts seen, advertise a generic estimator-derived confidence in a link-state protocol.

Cluster 6: multi-robot estimation (U)
  Consequence: useful for motivating the robotics use case. Not competing work.

----------------------------------------------------------------------
## 4. Revised novelty position

Do not claim as new
  - Adding trust or confidence to OLSR
  - Computing it from forwarding behaviour with a moving average
  - Penalizing or avoiding low-trust nodes, or combining hop count with trust
  - Letting avoided nodes recover (reputation fading)
  - Hysteresis in OLSR in general

Plausible claims, each conditional on your results and on the verification below
  1. A characterization of the reliability versus delay, path length, overhead and route-stability trade-off for confidence-aware OLSR, with acceptability limits fixed in advance and a Pareto presentation, across density, mobility, fraction of unreliable nodes and confidence volatility. The cited OLSR trust papers emphasize attack resilience; I did not see this framing in their abstracts.
  2. An estimator-agnostic confidence interface (the same routing layer accepts forwarding-derived or estimator-derived confidence). I did not find this in OLSR work.
  3. Route-level hysteresis for confidence-driven route changes, with a measured effect on route changes per minute.
  4. Conditions under which confidence-aware routing stops paying off (negative results).

Honest summary: the idea is not new; a well-executed characterization study could be. Whether it is new enough depends on the full texts of A, B, C and on a deeper search.

----------------------------------------------------------------------
## 5. Verification to-do list (do these before writing related work)

  1. Get full texts of A (TCAOLSR), B (OLSRT-C), C (TUE-OLSR), D (Lim et al.). For each, record: how the score is updated, how it enters the route cost, which metrics are reported, whether delay and hop count are reported, whether route changes are reported, whether alpha-like parameters are swept, which simulator.
  2. Confirm authors, years and venues marked "verify" (A, E, F, H, O, T).
  3. Run the search strings below on Google Scholar, IEEE Xplore, ACM DL and Scopus, and record how many relevant hits are new.
  4. Look for papers that cite A, B or C (forward citation search) in case a trade-off study already exists.
  5. Search specifically for "route flapping" and "trust" together, and for "hysteresis" and "trust-based routing" together.
  6. Decide whether to rename the work to avoid the TCAOLSR and OLSRT-C name overlap. A less colliding title: "Reliability-Cost Trade-offs of Dynamic Node-Confidence Routing in OLSR-Based MANETs".

Search strings
  "trust" "OLSR" "hysteresis" route changes
  "confidence" "OLSR" "path length" "delay" trade-off
  "dynamic trust" OR "time-varying trust" OLSR ns-3
  "reputation fading" OR "redemption" proactive routing OLSR
  "estimator" OR "Kalman" "confidence" routing MANET OR "ad hoc"
  "state uncertainty" routing "link state" MANET
  "quality of information" routing MANET
  "node reliability" metric OLSR "additive" OR "multiplicative" penalty
  "Pareto" reliability delay routing MANET trust
  "UAV" OR "FANET" OLSR trust node state

----------------------------------------------------------------------
## 6. Draft related-work skeleton (paraphrased; add citations after verifying)

  Trust and reputation in MANET routing. Early cooperation schemes monitor next-hop forwarding and steer traffic away from misbehaving nodes (Watchdog and Pathrater, CONFIDANT, CORE). Redemption mechanisms such as reputation fading let isolated nodes regain standing (CONFIDANT, Co-Agent). We adopt the same observation principle but study it as a continuous reliability estimate, not an attack detector.

  Trust-aware OLSR. Several works integrate trust into OLSR, through MPR selection (Lim et al.; S-OLSR) or route selection (TUE-OLSR, TCAOLSR, OLSRT-C, BT-OLSR). They are mostly framed around black hole, selfish or cooperative attacks and report delivery ratio, latency and overhead. [After full-text check: state which report hop count, delay trade-offs, route stability or parameter sensitivity, and which do not.] Our work differs by [your verified differences].

  Link-quality metrics and hysteresis in OLSR. ETX and hysteresis mechanisms in OLSRd operate on links and are known to affect route flapping (Johnson and Hancke). Our hysteresis operates on route cost when node confidence changes.

  Node attributes in OLSR metrics. Speed-weighted ETX (speed-aware UAV routing) and entropy-weighted MPR selection (CEL-OLSR) show that node attributes can enter OLSR decisions. We use a confidence derived from a node's own estimation or forwarding behaviour.

  Uncertainty-aware routing. Geographic routing under location error (Kwon and Shroff; Milocco et al.; Lim et al.) and age-of-information routing (Sawwan and Wu) account for information quality in forwarding decisions. We bring the same idea to link-state routing through a generic confidence interface.

----------------------------------------------------------------------
## 7. Reference list with locations (verify details when you download)

A  TCAOLSR: https://benthamdirect.com/content/journals/swcc/10.2174/2210327909666190327173502
B  OLSRT-C: https://alpha.eurekaselect.com/article/107663
C  TUE-OLSR (IEEE Access 8, 2020, DOI 10.1109/access.2020.2978143): https://doaj.org/article/c42f35165dad440bb3635b1056abdb3d
D  Lim, Lim, Ko, QShine 2017: https://eudl.eu/doi/10.1007/978-3-319-78078-8_12
E  BT-OLSR: https://researchgate.net/profile/Raghu-Potukuchi/publication/312353697_Trust_aware_cooperative_optimised_link_state_routing_protocol
F  S-OLSR: https://research.buaa.edu.cn/zh/publications/an-improved-security-olsr-protocol-against-black-hole-attack-base/
G  Trust-Neighbors-Based (OLSR): https://ww.univ-sba.dz/eedis/publications.php?id_pub=765
H  Alattar and Sailhan: https://publiweb.femto-st.fr/tntnet/entries/349/documents/author/data
I  Xia et al., AOTMDV: https://pure.ecnu.edu.cn/en/publications/impact-of-trust-model-on-on-demand-multi-path-routing-in-mobile-a/
J  CONFIDANT: https://infoscience.epfl.ch/record/33410
K, L  Reputation survey (arXiv): https://arxiv.org/pdf/1012.2529 ; Co-Agent: https://oldcitypublishing.com/?p=15780
M  OLSRd extensions: https://github.com/opentechinstitute/olsrd/blob/commotion/README-Olsr-Extensions
N  Johnson and Hancke: https://www.repository.up.ac.za/handle/2263/8797
O  Speed-aware routing for UAV ad hoc networks: https://arxiv.org/pdf/1307.6350
P  CEL-OLSR: https://doaj.org/article/f75d617ffcf64c14921c45dd65b96f9b
Q  Kwon and Shroff: https://docs.lib.purdue.edu/ecetr/130
R  Milocco et al.: https://ri.conicet.gov.ar/handle/11336/180523
S  Lim et al.: https://www.cl.cam.ac.uk/techreports/UCAM-CL-TR-629.html
T  Sawwan and Wu: https://cis.temple.edu/~wu/research/publications/Publication_files/1-s2.0-S1389128626001337-main.pdf
U  Greedy Kalman-Swarm: https://arxiv.org/pdf/2604.16868 ; Khodayi-mehr et al.: https://www.arxiv.org/abs/1805.01574v2
