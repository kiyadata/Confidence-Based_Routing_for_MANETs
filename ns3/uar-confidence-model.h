/*
 * uar-confidence-model.h
 *
 * Confidence SOURCE MODEL for UAR-Mesh.
 *
 * Why this exists: simulated ns-3 nodes have no real Kalman filter or GPS, so we
 * need something that produces a confidence score c(t) per node. This model
 * makes a chosen fraction of nodes "fragile": they drift between a good state
 * (c near 1) and a degraded state (c low), then recover. The rest stay near 1.
 *
 * Usage (in your scenario file):
 *
 *   #include "uar-confidence-model.h"
 *   ...
 *   UarConfidenceModel::Install(nNodes, 0.25 /*fraction fragile*/, 1.0 /*step s*/);
 *   ...
 *   double c = UarConfidenceModel::Get(nodeId);   // 0..1, quantized to 8 bits
 *
 * It is a process-wide singleton for simplicity (fine for simulation code).
 * Keep the same RNG seed handling as the rest of the scenario so runs repeat.
 *
 * To replay REAL estimator logs instead, replace Step() with a lookup into a
 * CSV of (time, nodeId, confidence). That makes a stronger paper.
 */

#ifndef UAR_CONFIDENCE_MODEL_H
#define UAR_CONFIDENCE_MODEL_H

#include "ns3/core-module.h"

#include <algorithm>
#include <cmath>
#include <vector>

namespace ns3
{

class UarConfidenceModel
{
  public:
    // Create the model and start its periodic update. Call once, before Simulator::Run().
    static void Install(uint32_t nNodes,
                        double fragileFraction,
                        double stepSeconds = 1.0,
                        double pDegrade = 0.02,  // chance per step a good fragile node degrades
                        double pRecover = 0.05)  // chance per step a degraded node recovers
    {
        Instance().Init(nNodes, fragileFraction, stepSeconds, pDegrade, pRecover);
    }

    // Current confidence of a node, quantized to 8 bits (what would go on the wire).
    static double Get(uint32_t nodeId)
    {
        UarConfidenceModel& m = Instance();
        if (nodeId >= m.m_c.size())
        {
            return 1.0;
        }
        return std::round(m.m_c[nodeId] * 255.0) / 255.0;
    }

    static uint8_t GetByte(uint32_t nodeId)
    {
        return static_cast<uint8_t>(std::round(Get(nodeId) * 255.0));
    }

    // For tests (e.g. the diamond topology): pin a node's confidence to a fixed value.
    // Call UarConfidenceModel::Install(...) first (use fraction 0), then Force(...).
    // Force() can be scheduled at any simulation time to change a node's score mid-run.
    static void Force(uint32_t nodeId, double c)
    {
        UarConfidenceModel& m = Instance();
        if (nodeId < m.m_c.size())
        {
            m.m_c[nodeId] = c;
            m.m_target[nodeId] = c;
            m.m_forced[nodeId] = true;
        }
    }

    static bool IsFragile(uint32_t nodeId)
    {
        UarConfidenceModel& m = Instance();
        return nodeId < m.m_fragile.size() && m.m_fragile[nodeId];
    }

  private:
    static UarConfidenceModel& Instance()
    {
        static UarConfidenceModel inst;
        return inst;
    }

    void Init(uint32_t n, double frac, double step, double pDeg, double pRec)
    {
        m_step = step;
        m_pDegrade = pDeg;
        m_pRecover = pRec;
        m_rv = CreateObject<UniformRandomVariable>();
        m_c.assign(n, 1.0);
        m_target.assign(n, 1.0);
        m_fragile.assign(n, false);
        m_degraded.assign(n, false);
        m_forced.assign(n, false);

        // choose which nodes are fragile
        uint32_t k = static_cast<uint32_t>(std::round(frac * n));
        uint32_t chosen = 0;
        while (chosen < k)
        {
            uint32_t i = m_rv->GetInteger(0, n - 1);
            if (!m_fragile[i])
            {
                m_fragile[i] = true;
                ++chosen;
            }
        }
        Simulator::Schedule(Seconds(m_step), &UarConfidenceModel::Step, this);
    }

    void Step()
    {
        for (uint32_t i = 0; i < m_c.size(); ++i)
        {
            if (m_forced[i])
            {
                continue; // pinned by Force(): leave untouched
            }
            if (m_fragile[i])
            {
                if (!m_degraded[i] && m_rv->GetValue() < m_pDegrade)
                {
                    m_degraded[i] = true;
                    m_target[i] = m_rv->GetValue(0.05, 0.40); // how bad it gets
                }
                else if (m_degraded[i] && m_rv->GetValue() < m_pRecover)
                {
                    m_degraded[i] = false;
                    m_target[i] = 1.0;
                }
            }
            else
            {
                m_target[i] = m_rv->GetValue(0.90, 1.0); // healthy nodes jitter slightly
            }
            // first-order smoothing toward the target (prevents instant jumps)
            m_c[i] += 0.3 * (m_target[i] - m_c[i]);
            m_c[i] = std::min(1.0, std::max(0.0, m_c[i]));
        }
        Simulator::Schedule(Seconds(m_step), &UarConfidenceModel::Step, this);
    }

    double m_step{1.0};
    double m_pDegrade{0.02};
    double m_pRecover{0.05};
    Ptr<UniformRandomVariable> m_rv;
    std::vector<double> m_c;
    std::vector<double> m_target;
    std::vector<bool> m_fragile;
    std::vector<bool> m_degraded;
    std::vector<bool> m_forced;
};

} // namespace ns3

#endif // UAR_CONFIDENCE_MODEL_H
