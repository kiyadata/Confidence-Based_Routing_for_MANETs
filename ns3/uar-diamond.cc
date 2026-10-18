/*
 * uar-diamond.cc
 *
 * The first test your confidence-aware OLSR must pass.
 *
 *            A
 *          /   \
 *        S       D          four static nodes: S (source), A, B, D (destination)
 *          \   /
 *            B
 *
 * Node ids:  S = 0, A = 1, B = 2, D = 3.
 *
 * Timeline
 *   t = 0   Force A to c = 0.2 (bad) and B to c = 1.0 (good)
 *   t = 40  print S's routing table        EXPECTED with confidence-aware routing: S -> D via B
 *   t = 60  Force A to c = 1.0 and B to c = 0.2
 *   t = 100 print S's routing table        EXPECTED: S -> D via A (after hysteresis margin)
 *
 * With STOCK OLSR (what this file builds by default) confidence is ignored, so the
 * route stays on whichever of A or B stock OLSR picked. That is your control result.
 * Once your uar-olsr module exists, change the two lines marked SWITCH HERE and the
 * route should follow the confidence.
 *
 * Copy into ns-3 scratch/ together with uar-confidence-model.h and run:
 *   ./ns3 run "uar-diamond"
 *
 * Geometry note: S and D must NOT hear each other directly, but each must hear A and B.
 * If the table shows D as a direct neighbour of S, increase --spacing; if S cannot reach
 * anything, decrease it or raise --txPower. Default Wi-Fi range is only tens of metres.
 *
 * Written for ns-3.36 or newer. Not compiled where it was written: fix small API
 * differences as the compiler reports them.
 */

#include "uar-confidence-model.h"

#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/network-module.h"
#include "ns3/olsr-helper.h" // SWITCH HERE: include your uar-olsr helper header instead
#include "ns3/wifi-module.h"

#include <iostream>

using namespace ns3;

int
main(int argc, char* argv[])
{
    double spacing = 1.0;  // scales the whole diamond
    double txPower = 16.0; // dBm
    double simTime = 110.0;
    CommandLine cmd(__FILE__);
    cmd.AddValue("spacing", "Scale factor for the diamond geometry", spacing);
    cmd.AddValue("txPower", "Tx power (dBm)", txPower);
    cmd.Parse(argc, argv);

    NodeContainer nodes;
    nodes.Create(4); // 0=S, 1=A, 2=B, 3=D

    WifiHelper wifi;
    wifi.SetStandard(WIFI_STANDARD_80211b);
    wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager",
                                 "DataMode", StringValue("DsssRate11Mbps"),
                                 "ControlMode", StringValue("DsssRate1Mbps"));
    YansWifiPhyHelper phy;
    YansWifiChannelHelper channel = YansWifiChannelHelper::Default();
    phy.SetChannel(channel.Create());
    phy.Set("TxPowerStart", DoubleValue(txPower));
    phy.Set("TxPowerEnd", DoubleValue(txPower));
    WifiMacHelper mac;
    mac.SetType("ns3::AdhocWifiMac");
    NetDeviceContainer devices = wifi.Install(phy, mac, nodes);

    // fixed positions
    Ptr<ListPositionAllocator> pos = CreateObject<ListPositionAllocator>();
    pos->Add(Vector(0.0 * spacing, 0.0, 0.0));     // S
    pos->Add(Vector(30.0 * spacing, 20.0, 0.0));   // A
    pos->Add(Vector(30.0 * spacing, -20.0, 0.0));  // B
    pos->Add(Vector(60.0 * spacing, 0.0, 0.0));    // D
    MobilityHelper mobility;
    mobility.SetPositionAllocator(pos);
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(nodes);

    // SWITCH HERE: replace OlsrHelper with your UarOlsrHelper
    OlsrHelper routing;
    InternetStackHelper stack;
    stack.SetRoutingHelper(routing);
    stack.Install(nodes);

    Ipv4AddressHelper address;
    address.SetBase("10.1.0.0", "255.255.0.0");
    address.Assign(devices);

    // confidence: model with no random fragile nodes, then pin values by hand
    UarConfidenceModel::Install(4, 0.0, 1.0);
    UarConfidenceModel::Force(1, 0.2); // A bad
    UarConfidenceModel::Force(2, 1.0); // B good
    UarConfidenceModel::Force(0, 1.0);
    UarConfidenceModel::Force(3, 1.0);

    Simulator::Schedule(Seconds(60.0), []() {
        UarConfidenceModel::Force(1, 1.0); // A recovers
        UarConfidenceModel::Force(2, 0.2); // B degrades
    });

    // print S's routing table twice
    Ptr<OutputStreamWrapper> out = Create<OutputStreamWrapper>(&std::cout);
    Ipv4RoutingHelper::PrintRoutingTableAt(Seconds(40.0), nodes.Get(0), out);
    Ipv4RoutingHelper::PrintRoutingTableAt(Seconds(100.0), nodes.Get(0), out);

    std::cout << "Node ids: S=0 A=1 B=2 D=3. Look at the route to D's address (10.1.0.4).\n"
              << "Gateway column shows the next hop: A = 10.1.0.2, B = 10.1.0.3.\n";

    Simulator::Stop(Seconds(simTime));
    Simulator::Run();
    Simulator::Destroy();
    return 0;
}
