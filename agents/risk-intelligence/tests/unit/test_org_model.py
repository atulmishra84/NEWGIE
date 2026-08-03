from risk_intelligence.domain.engine import calculate_risk

def test_custom_weights_change_score(sample_bundle):
    base = calculate_risk(sample_bundle)
    sample_bundle.org_risk_model = {"model_id": "strict-pi", "weights": {"prompt_injection": 2.0, "autonomy": 2.0}}
    strict = calculate_risk(sample_bundle)
    assert strict.category_scores["prompt_injection"] >= base.category_scores["prompt_injection"]
