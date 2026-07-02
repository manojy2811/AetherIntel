import pytest
from app.state import append_reducer, update_dict_reducer, ResearchState
from app.graph import route_next

def test_append_reducer():
    assert append_reducer(None, [{"data": 1}]) == [{"data": 1}]
    assert append_reducer([{"data": 1}], [{"data": 2}]) == [{"data": 1}, {"data": 2}]
    assert append_reducer([{"data": 1}], None) == [{"data": 1}]

def test_update_dict_reducer():
    assert update_dict_reducer(None, {"key1": "val1"}) == {"key1": "val1"}
    assert update_dict_reducer({"key1": "val1"}, {"key2": "val2"}) == {"key1": "val1", "key2": "val2"}
    assert update_dict_reducer({"key1": "val1"}, {"key1": "new_val"}) == {"key1": "new_val"}

def test_route_next():
    # Test routing logic based on state status
    state1: ResearchState = {
        "research_query": "AAPL details",
        "gathered_raw_data": [],
        "financial_metrics": {},
        "report_markdown": "",
        "agent_history": [],
        "current_status": "Routing flow to researcher",
        "feedback": None,
        "next_node_override": None
    }
    assert route_next(state1) == "researcher"

    state2 = state1.copy()
    state2["current_status"] = "Routing flow to analyst"
    assert route_next(state2) == "analyst"

    state3 = state1.copy()
    state3["current_status"] = "Routing flow to critic"
    assert route_next(state3) == "critic"

    state4 = state1.copy()
    state4["current_status"] = "Finished workflow"
    assert route_next(state4) == "__end__"
