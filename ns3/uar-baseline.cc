/*
 * uar-baseline.cc
 *
 * Baseline MANET scenario for the UAR-Mesh project (no confidence yet).
 * Copy this file into  ns-3-dev/scratch/  and run:
 *
 *   ./ns3 run "uar-baseline --proto=olsr --nNodes=30 --speed=5 --run=1"
 *
 * It measures, per run:
 *   - data packet delivery ratio (PDR)
 *   - mean end-to-end delay
 *   - routing control overhead (bytes), found by classifying FlowMonitor flows
 *     on the OLSR (UDP 698) and AODV (UDP 654) ports
 * and appends one line to a CSV file.
 *
 * Written for ns-3.36 or newer (CMake build, ./ns3 wrapper). NOT compiled in the
 * environment where it was written, so expect to fix small API differences
 * between ns-3 versions. Compiler errors will tell you exactly what.
 *
 * Tuning note: with default Wi-Fi settings the radio range is only tens of
 * metres. If flows never connect, shrink --area or raise --txPower.
 */

#include "ns3/aodv-helper.h"
#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/network-module.h"
#include "ns3/olsr-helper.h"
#include "ns3/wifi-module.h"

#include <algorithm>
#include <fstream>
#include <iostream>
#include <sstream>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("UarBaseline");

int
main(int argc, char* argv[])
{
    // ---- parameters (override on the command line) ----
    uint32_t nNodes = 30;
    uint32_t nFlows = 5;
    double simTime = 200.0;   // seconds
    double area = 300.0;      // square side, metres
    double speed = 5.0;       // max speed, m/s (min speed fixed at 1 m/s)
    double txPower = 16.0;    // dBm
    uint32_t run = 1;         // RNG run number: change it to get a new random seed
    std::string proto = "olsr";
    std::string outCsv = "baseline.csv";

    CommandLine cmd(__FILE__);
    cmd.AddValue("nNodes", "Number of nodes", nNodes);
    cmd.AddValue("nFlows", "Number of UDP flows", nFlows);
    cmd.AddValue("simTime", "Simulation time (s)", simTime);
    cmd.AddValue("area", "Square area side (m)", area);
    cmd.AddValue("speed", "Max node speed (m/s)", speed);
    cmd.AddValue("txPower", "Tx power (dBm)", txPower);
    cmd.AddValue("run", "RNG run number", run);
    cmd.AddValue("proto", "olsr or aodv", proto);
    cmd.AddValue("outCsv", "Output CSV file", outCsv);
    cmd.Parse(argc, argv);

    RngSeedManager::SetSeed(12345);
    RngSeedManager::SetRun(run);

    // ---- nodes ----
    NodeContainer nodes;
    nodes.Create(nNodes);

    // ---- Wi-Fi ad hoc (802.11b) ----
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

    // ---- mobility: random waypoint in a square ----
    ObjectFactory posFactory;
    posFactory.SetTypeId("ns3::RandomRectanglePositionAllocator");
    std::ostringstream xs;
    std::ostringstream ys;
    xs << "ns3::UniformRandomVariable[Min=0.0|Max=" << area << "]";
    ys << "ns3::UniformRandomVariable[Min=0.0|Max=" << area << "]";
    posFactory.Set("X", StringValue(xs.str()));
    posFactory.Set("Y", StringValue(ys.str()));
    Ptr<PositionAllocator> alloc = posFactory.Create()->GetObject<PositionAllocator>();

    std::ostringstream speedStr;
    speedStr << "ns3::UniformRandomVariable[Min=1.0|Max=" << std::max(speed, 1.5) << "]";

    MobilityHelper mobility;
    mobility.SetMobilityModel("ns3::RandomWaypointMobilityModel",
                              "Speed", StringValue(speedStr.str()),
                              "Pause", StringValue("ns3::ConstantRandomVariable[Constant=0.0]"),
                              "PositionAllocator", PointerValue(alloc));
    mobility.SetPositionAllocator(alloc);
    mobility.Install(nodes);

    // ---- internet stack + routing protocol ----
    InternetStackHelper stack;
    if (proto == "aodv")
    {
        AodvHelper aodv;
        stack.SetRoutingHelper(aodv);
    }
    else
    {
        OlsrHelper olsr;
        stack.SetRoutingHelper(olsr);
    }
    stack.Install(nodes);

    Ipv4AddressHelper address;
    address.SetBase("10.1.0.0", "255.255.0.0");
    Ipv4InterfaceContainer ifaces = address.Assign(devices);

    // ---- traffic: nFlows random source/destination UDP flows ----
    Ptr<UniformRandomVariable> rv = CreateObject<UniformRandomVariable>();
    for (uint32_t f = 0; f < nFlows; ++f)
    {
        uint32_t src = rv->GetInteger(0, nNodes - 1);
        uint32_t dst = rv->GetInteger(0, nNodes - 1);
        while (dst == src)
        {
            dst = rv->GetInteger(0, nNodes - 1);
        }
        uint16_t port = 9000 + f; // one port per flow so sinks never collide

        PacketSinkHelper sink("ns3::UdpSocketFactory",
                              InetSocketAddress(Ipv4Address::GetAny(), port));
        ApplicationContainer sinkApp = sink.Install(nodes.Get(dst));
        sinkApp.Start(Seconds(0.0));
        sinkApp.Stop(Seconds(simTime));

        OnOffHelper onoff("ns3::UdpSocketFactory",
                          InetSocketAddress(ifaces.GetAddress(dst), port));
        onoff.SetConstantRate(DataRate("32kbps"), 512);
        ApplicationContainer app = onoff.Install(nodes.Get(src));
        app.Start(Seconds(30.0 + rv->GetValue(0.0, 10.0))); // let routing warm up first
        app.Stop(Seconds(simTime - 5.0));
    }

    // ---- measurement ----
    FlowMonitorHelper fmHelper;
    Ptr<FlowMonitor> monitor = fmHelper.InstallAll();

    Simulator::Stop(Seconds(simTime));
    Simulator::Run();

    monitor->CheckForLostPackets();
    Ptr<Ipv4FlowClassifier> classifier = DynamicCast<Ipv4FlowClassifier>(fmHelper.GetClassifier());

    double dataTx = 0;
    double dataRx = 0;
    double delaySum = 0;
    double ctrlTxBytes = 0;
    double ctrlTxPkts = 0;

    for (const auto& kv : monitor->GetFlowStats())
    {
        Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow(kv.first);
        const FlowMonitor::FlowStats& s = kv.second;
        if (t.destinationPort == 698 || t.destinationPort == 654)
        {
            // routing control traffic (OLSR = 698, AODV = 654)
            ctrlTxBytes += s.txBytes;
            ctrlTxPkts += s.txPackets;
        }
        else if (t.destinationPort >= 9000)
        {
            dataTx += s.txPackets;
            dataRx += s.rxPackets;
            delaySum += s.delaySum.GetSeconds();
        }
    }

    double pdr = (dataTx > 0) ? dataRx / dataTx : 0.0;
    double meanDelay = (dataRx > 0) ? delaySum / dataRx : 0.0;

    std::cout << "proto=" << proto << " nodes=" << nNodes << " speed=" << speed
              << " run=" << run << " PDR=" << pdr << " delay(s)=" << meanDelay
              << " ctrlBytes=" << ctrlTxBytes << " ctrlPkts=" << ctrlTxPkts << std::endl;

    bool newFile = !std::ifstream(outCsv).good();
    std::ofstream out(outCsv, std::ios::app);
    if (newFile)
    {
        out << "proto,nNodes,speed,run,pdr,meanDelay,ctrlBytes,ctrlPkts\n";
    }
    out << proto << "," << nNodes << "," << speed << "," << run << "," << pdr << ","
        << meanDelay << "," << ctrlTxBytes << "," << ctrlTxPkts << "\n";

    Simulator::Destroy();
    return 0;
}
