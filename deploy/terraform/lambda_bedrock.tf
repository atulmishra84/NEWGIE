# ── Lambda: single shared function for all Bedrock Agent action groups ─────────
# All 15 agents route to this one Lambda. The handler uses actionGroup + function
# to dispatch to the correct agent-specific logic within the zip package.

resource "aws_lambda_function" "gie_bedrock_agents" {
  function_name = "gie-bedrock-agents-${var.environment}"
  description   = "Unified action-group handler for all 15 GIE Bedrock Agents"
  role          = aws_iam_role.lambda_execution.arn

  filename         = "${path.module}/../../dist/gie_bedrock_agents.zip"
  source_code_hash = filebase64sha256("${path.module}/../../dist/gie_bedrock_agents.zip")

  handler = "dispatcher.lambda_handler"
  runtime = "python3.12"
  timeout = 60
  memory_size = 512

  environment {
    variables = {
      GIE_ENVIRONMENT    = var.environment
      BEDROCK_MODEL_ID   = var.bedrock_foundation_model
      LOG_LEVEL          = var.environment == "production" ? "WARNING" : "DEBUG"
    }
  }

  tags = merge(local.common_tags, {
    Name = "gie-bedrock-agents-${var.environment}"
  })
}

resource "aws_cloudwatch_log_group" "gie_bedrock_agents" {
  name              = "/aws/lambda/${aws_lambda_function.gie_bedrock_agents.function_name}"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}
