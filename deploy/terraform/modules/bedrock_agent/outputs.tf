output "agent_id" {
  description = "Bedrock Agent ID"
  value       = aws_bedrockagent_agent.this.agent_id
}

output "agent_arn" {
  description = "Bedrock Agent ARN"
  value       = aws_bedrockagent_agent.this.agent_arn
}

output "alias_id" {
  description = "Live alias ID (use this for InvokeAgent API calls)"
  value       = aws_bedrockagent_agent_alias.live.agent_alias_id
}

output "alias_arn" {
  description = "Live alias ARN"
  value       = aws_bedrockagent_agent_alias.live.agent_alias_arn
}
