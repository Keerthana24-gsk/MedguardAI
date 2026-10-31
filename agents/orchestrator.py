"""Orchestrator: LangGraph if installed (else sequential fallback), with retries and a human checkpoint between stages."""
import time
from . import prescription_agent, normalization_agent, reconciliation_agent, interaction_agent, evidence_agent, report_agent
def retry(fn, n=3):
    def wrapped(s):
        for i in range(n):
            try: return fn(s)
            except Exception as e:
                if i == n - 1: s.setdefault("warnings", []).append(f"{fn.__module__} failed: {e}"); return s
                time.sleep(0.5)
    return wrapped
def _compile(nodes):
    try:
        from langgraph.graph import StateGraph, START, END
        g, prev = StateGraph(dict), START
        for name, fn in nodes:
            g.add_node(name, fn); g.add_edge(prev, name); prev = name
        g.add_edge(prev, END)
        return g.compile().invoke
    except ImportError:
        def seq(s):
            for _, fn in nodes: s = fn(s)
            return s
        return seq
STAGE1 = _compile([(n, retry(m.run)) for n, m in [("extract", prescription_agent), ("normalize", normalization_agent), ("reconcile", reconciliation_agent)]])
STAGE2 = _compile([(n, retry(m.run)) for n, m in [("reconcile", reconciliation_agent), ("interact", interaction_agent), ("evidence", evidence_agent), ("report", report_agent)]])
def stage1(state): return STAGE1(state)   # then: human confirmation checkpoint (UI)
def stage2(state): return STAGE2(state)
