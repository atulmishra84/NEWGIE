# ── Outputs: all 15 Bedrock Agent IDs and aliases ────────────────────────────
# Use alias_id (not agent_id) when calling InvokeAgent from application code.

output "bedrock_agents" {
  description = "Map of agent name → {agent_id, alias_id} for all 15 GIE agents"
  value = {
    context_intelligence         = { agent_id = module.context_intelligence.agent_id,         alias_id = module.context_intelligence.alias_id }
    knowledge_intelligence       = { agent_id = module.knowledge_intelligence.agent_id,       alias_id = module.knowledge_intelligence.alias_id }
    risk_intelligence            = { agent_id = module.risk_intelligence.agent_id,            alias_id = module.risk_intelligence.alias_id }
    policy_intelligence          = { agent_id = module.policy_intelligence.agent_id,          alias_id = module.policy_intelligence.alias_id }
    compliance_intelligence      = { agent_id = module.compliance_intelligence.agent_id,      alias_id = module.compliance_intelligence.alias_id }
    recommendation_intelligence  = { agent_id = module.recommendation_intelligence.agent_id,  alias_id = module.recommendation_intelligence.alias_id }
    explainability_intelligence  = { agent_id = module.explainability_intelligence.agent_id,  alias_id = module.explainability_intelligence.alias_id }
    validation_intelligence      = { agent_id = module.validation_intelligence.agent_id,      alias_id = module.validation_intelligence.alias_id }
    learning_intelligence        = { agent_id = module.learning_intelligence.agent_id,        alias_id = module.learning_intelligence.alias_id }
    integration_intelligence     = { agent_id = module.integration_intelligence.agent_id,     alias_id = module.integration_intelligence.alias_id }
    policy_generator             = { agent_id = module.policy_generator.agent_id,             alias_id = module.policy_generator.alias_id }
    orchestrator                 = { agent_id = module.orchestrator.agent_id,                 alias_id = module.orchestrator.alias_id }
    chief_orchestrator           = { agent_id = module.chief_orchestrator.agent_id,           alias_id = module.chief_orchestrator.alias_id }
    policy_engine                = { agent_id = module.policy_engine.agent_id,               alias_id = module.policy_engine.alias_id }
    risk_assessment              = { agent_id = module.risk_assessment.agent_id,              alias_id = module.risk_assessment.alias_id }
  }
}

output "lambda_function_arn" {
  description = "ARN of the shared Lambda handling all agent action groups"
  value       = aws_lambda_function.gie_bedrock_agents.arn
}

output "lambda_function_name" {
  description = "Name of the shared Lambda function"
  value       = aws_lambda_function.gie_bedrock_agents.function_name
}

output "bedrock_agent_role_arn" {
  description = "IAM role ARN assumed by all Bedrock Agents"
  value       = aws_iam_role.bedrock_agent.arn
}
