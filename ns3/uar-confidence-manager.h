/*
 * uar-confidence-manager.h
 *
 * Dynamic confidence for Confidence-Aware OLSR (research plan v2).
 * Header-only. Mirrors the Python prototype uar_dynamic.py so results can be
 * compared between the two.
 *
 * Two separate quantities per node:
 *
 *   TRUE reliability r_i(t)   hidden ground truth. Fragile nodes degrade and
 *                             recover over time. A node with low r_i really drops
 *                             a share (1 - r_i) of the transit packets it should
 *                             forward. This is FAULT INJECTION, and it is what makes
 *                             PDR respond to the idea.
 *
 *   CONFIDENCE C_i(t)         what the node COMPUTES and advertises. Built from
 *                             observed forwarding success with an exponential moving
 *                             average:
 *                                 C_i <- lambda * C_i + (1 - lambda) * F_i
 *                             F_i = successes / attempts during the last step.
 *                             With no attempts in a step, C_i drifts toward 1 by
 *                             `recovery`, otherwise an avoided node would never be
 *                             re-tested and could never regain confidence.
 *
 * How to use it
 *   1. In your scenario, before Simulator::Run():
 *        UarConfidenceManager::Install(nNodes, 0.25 /*fragile fraction*/);
 *   2. In your routing protocol, where a node is about to FORWARD a transit data
 *      packet (not one it originates, not one addressed to itself):
 *        if (UarConfidenceManager::ShouldDrop(nodeId)) { drop the packet; return; }
 *      ShouldDrop() also records the attempt and its outcome for the EMA.
 *   3. When building HELLO/TC messages:
 *        msg.confidence = UarConfidenceManager::GetByte(nodeId);
 *   4. In route computation, read the advertised table, not this class
 *      (other nodes only know what was advertised).
 *
 * Important modelling note: here a node measures its own forwarding success
 * (self-assessed). A later extension is neighbour observation (a watchdog that
 * overhears whether the next hop really forwarded). Say which one you used.
 *
 * Not compiled where it was written; fix small API differences as needed.
 */

#ifndef UAR_CONFIDENCE_MANAGER_H
#define UAR_CONFIDENCE_MANAGER_H

#include "ns3/core-module.h"

#include <algorithm>
#include <cmath>
#include <vector>

namespace ns3
{

class UarConfidenceManager
{
  public:
    static void Install(uint32_t nNodes,
                        double fragileFraction,
                        double lambda = 0.8,
                        double recovery = 0.02,
                        double stepSeconds = 1.0,
                        double pDegrade = 0.04,  // per step, healthy fragile node starts degrading
                        double pRecover = 0.02)  // per step, degraded node starts recovering
    {
        Instance().Init(nNodes, fragileFraction, lambda, recovery, stepSeconds, pDegrade, pRecover);
    }

    // Advertised confidence, quantized to 8 bits as it would be on the wire.
    static double Get(uint32_t id)
    {
        UarConfidenceManager& m = Instance();
        return id < m.m_conf.size() ? std::round(m.m_conf[id] * 255.0) / 255.0 : 1.0;
    }

    static uint8_t GetByte(uint32_t id)
    {
        return static_cast<uint8_t>(std::round(Get(id) * 255.0));
    }

    // Ground truth, for logging and metrics only. Routing must never read this.
    static double TrueReliability(uint32_t id)
    {
        UarConfidenceManager& m = Instance();
        return id < m.m_r.size() ? m.m_r[id] : 1.0;
    }

    // Call when node `id` is about to forward a transit data packet.
    // Returns true if the packet must be dropped (fault injection). Also records the
    // attempt and outcome for the confidence estimate.
    static bool ShouldDrop(uint32_t id)
    {
        UarConfidenceManager& m = Instance();
        if (id >= m.m_r.size())
        {
            return false;
        }
        m.m_attempts[id]++;
        bool ok = m.m_rv->GetValue() < m.m_r[id];
        if (ok)
        {
            m.m_success[id]++;
        }
        return !ok;
    }

    // Pin a node's true reliability (tests, e.g. the diamond topology).
    static void ForceTrueReliability(uint32_t id, double r)
    {
        UarConfidenceManager& m = Instance();
        if (id < m.m_r.size())
        {
            m.m_r[id] = r;
            m.m_target[id] = r;
            m.m_forced[id] = true;
        }
    }

  private:
    static UarConfidenceManager& Instance()
    {
        static UarConfidenceManager inst;
        return inst;
    }

    void Init(uint32_t n, double frac, double lambda, double recovery, double step, double pDeg, double pRec)
    {
        m_lambda = lambda;
        m_recovery = recovery;
        m_step = step;
        m_pDeg = pDeg;
        m_pRec = pRec;
        m_rv = CreateObject<UniformRandomVariable>();
        m_r.assign(n, 0.98);
        m_target.assign(n, 0.98);
        m_conf.assign(n, 1.0);
        m_attempts.assign(n, 0);
        m_success.assign(n, 0);
        m_fragile.assign(n, false);
        m_degraded.assign(n, false);
        m_forced.assign(n, false);

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
        Simulator::Schedule(Seconds(m_step), &UarConfidenceManager::Step, this);
    }

    void Step()
    {
        for (uint32_t i = 0; i < m_r.size(); ++i)
        {
            // 1. evolve the hidden true reliability
            if (!m_forced[i])
            {
                if (m_fragile[i])
                {
                    if (!m_degraded[i] && m_rv->GetValue() < m_pDeg)
                    {
                        m_degraded[i] = true;
                        m_target[i] = m_rv->GetValue(0.10, 0.50);
                    }
                    else if (m_degraded[i] && m_rv->GetValue() < m_pRec)
                    {
                        m_degraded[i] = false;
                        m_target[i] = 0.98;
                    }
                }
                m_r[i] += 0.3 * (m_target[i] - m_r[i]);
            }

            // 2. update the advertised confidence from observed forwarding
            if (m_attempts[i] > 0)
            {
                double f = static_cast<double>(m_success[i]) / m_attempts[i];
                m_conf[i] = m_lambda * m_conf[i] + (1.0 - m_lambda) * f;
            }
            else
            {
                m_conf[i] += m_recovery * (1.0 - m_conf[i]);
            }
            m_conf[i] = std::min(1.0, std::max(0.0, m_conf[i]));
            m_attempts[i] = 0;
            m_success[i] = 0;
        }
        Simulator::Schedule(Seconds(m_step), &UarConfidenceManager::Step, this);
    }

    double m_lambda{0.8};
    double m_recovery{0.02};
    double m_step{1.0};
    double m_pDeg{0.04};
    double m_pRec{0.02};
    Ptr<UniformRandomVariable> m_rv;
    std::vector<double> m_r;
    std::vector<double> m_target;
    std::vector<double> m_conf;
    std::vector<uint32_t> m_attempts;
    std::vector<uint32_t> m_success;
    std::vector<bool> m_fragile;
    std::vector<bool> m_degraded;
    std::vector<bool> m_forced;
};

} // namespace ns3

#endif // UAR_CONFIDENCE_MANAGER_H
