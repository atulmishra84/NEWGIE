from learning_intelligence.domain.ingest import collect_feedback

def test_collects_all_signal_types(sample_bundle):
    events = collect_feedback(sample_bundle)
    types = {e.feedback_type.value for e in events}
    assert "false_positive" in types
    assert "false_negative" in types
    assert "threat_intelligence" in types
    assert "regulatory_update" in types
