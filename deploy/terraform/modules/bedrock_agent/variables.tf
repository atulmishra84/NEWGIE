variable "agent_name" {
  description = "Unique name for the Bedrock Agent (kebab-case GIE service name)"
  type        = string
}

variable "description" {
  description = "Human-readable description surfaced in the Bedrock console"
  type        = string
}

variable "instruction" {
  description = "System prompt / instruction for the agent"
  type        = string
}

variable "foundation_model" {
  description = "Bedrock model ID to use for this agent"
  type        = string
  default     = "anthropic.claude-3-haiku-20240307-v1:0"
}

variable "agent_role_arn" {
  description = "IAM role ARN the Bedrock Agent assumes at runtime"
  type        = string
}

variable "lambda_arn" {
  description = "ARN of the Lambda function that executes action-group invocations"
  type        = string
}

variable "action_groups" {
  description = "Map of action-group name → {description, functions}"
  type = map(object({
    description = string
    functions = map(object({
      description = string
      parameters = map(object({
        type        = string
        description = string
        required    = bool
      }))
    }))
  }))
}

variable "environment" {
  description = "Deployment environment tag (dev | staging | production)"
  type        = string
}

variable "tags" {
  description = "Additional resource tags"
  type        = map(string)
  default     = {}
}
