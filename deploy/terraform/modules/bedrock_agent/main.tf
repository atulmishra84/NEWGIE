terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }
}

# ── Bedrock Agent ─────────────────────────────────────────────────────────────

resource "aws_bedrockagent_agent" "this" {
  agent_name              = var.agent_name
  description             = var.description
  instruction             = var.instruction
  foundation_model        = var.foundation_model
  agent_resource_role_arn = var.agent_role_arn
  idle_session_ttl_in_seconds = 600

  tags = merge(var.tags, {
    GIEAgent    = var.agent_name
    Environment = var.environment
  })
}

# ── Action Groups (one per logical capability group) ──────────────────────────

resource "aws_bedrockagent_agent_action_group" "groups" {
  for_each = var.action_groups

  agent_id          = aws_bedrockagent_agent.this.agent_id
  agent_version     = "DRAFT"
  action_group_name = each.key
  description       = each.value.description

  action_group_executor {
    lambda = var.lambda_arn
  }

  function_schema {
    member_functions {
      dynamic "functions" {
        for_each = each.value.functions
        content {
          name        = functions.key
          description = functions.value.description

          dynamic "parameters" {
            for_each = functions.value.parameters
            content {
              map_block_key = parameters.key
              type          = parameters.value.type
              description   = parameters.value.description
              required      = parameters.value.required
            }
          }
        }
      }
    }
  }

  depends_on = [aws_bedrockagent_agent.this]
}

# ── Allow Bedrock to invoke the action-group Lambda ───────────────────────────

resource "aws_lambda_permission" "bedrock_invoke" {
  statement_id  = "AllowBedrock-${var.agent_name}"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_arn
  principal     = "bedrock.amazonaws.com"
  source_arn    = aws_bedrockagent_agent.this.agent_arn
}

# ── Prepare + publish the DRAFT version as "v1" ───────────────────────────────

resource "aws_bedrockagent_agent_alias" "live" {
  agent_id         = aws_bedrockagent_agent.this.agent_id
  agent_alias_name = "live"
  description      = "Production alias for ${var.agent_name}"

  tags = merge(var.tags, {
    GIEAgent    = var.agent_name
    Environment = var.environment
  })

  depends_on = [aws_bedrockagent_agent_action_group.groups]
}
