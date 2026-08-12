# ── Lambda: single shared function for all Bedrock Agent action groups ─────────
# All 15 agents route to this one Lambda. The handler uses actionGroup + function
# to dispatch to the correct agent-specific logic within the zip package.
#
# The archive_file data source zips the handler sources at plan/apply time —
# no pre-built artifact or build script is required in the repo.

data "archive_file" "gie_bedrock_agents" {
  type        = "zip"
  source_dir  = "${path.module}/../aws/lambda_handlers"
  output_path = "${path.module}/../../.terraform/tmp/gie_bedrock_agents.zip"
  excludes    = ["__pycache__", "*.pyc"]
}

resource "aws_lambda_function" "gie_bedrock_agents" {
  function_name = "gie-bedrock-agents-${var.environment}"
  description   = "Unified action-group handler for all 15 GIE Bedrock Agents"
  role          = aws_iam_role.lambda_execution.arn

  filename         = data.archive_file.gie_bedrock_agents.output_path
  source_code_hash = data.archive_file.gie_bedrock_agents.output_base64sha256

  handler     = "dispatcher.lambda_handler"
  runtime     = "python3.12"
  timeout     = 60
  memory_size = 512

  environment {
    variables = {
      GIE_ENVIRONMENT  = var.environment
      BEDROCK_MODEL_ID = var.bedrock_foundation_model
      LOG_LEVEL        = var.environment == "production" ? "WARNING" : "DEBUG"
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
