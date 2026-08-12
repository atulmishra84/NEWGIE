# ── IAM: Bedrock Agent execution role ─────────────────────────────────────────
# One shared role; each agent is tagged with its own name but they all call
# the same Lambda function, so a single trust policy + permission set is fine.

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
}

resource "aws_iam_role" "bedrock_agent" {
  name = "gie-bedrock-agent-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowBedrockToAssume"
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = local.account_id
          }
        }
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "gie-bedrock-agent-role-${var.environment}"
  })
}

resource "aws_iam_role_policy" "bedrock_agent_policy" {
  name = "gie-bedrock-agent-policy"
  role = aws_iam_role.bedrock_agent.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "InvokeFoundationModel"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
        ]
        Resource = "arn:aws:bedrock:${local.region}::foundation-model/${var.bedrock_foundation_model}"
      },
      {
        Sid    = "InvokeLambdaActionGroup"
        Effect = "Allow"
        Action = ["lambda:InvokeFunction"]
        Resource = aws_lambda_function.gie_bedrock_agents.arn
      }
    ]
  })
}

# ── IAM: Lambda execution role ─────────────────────────────────────────────────

resource "aws_iam_role" "lambda_execution" {
  name = "gie-bedrock-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowLambdaToAssume"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "gie-bedrock-lambda-role-${var.environment}"
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_bedrock_invoke" {
  name = "gie-lambda-bedrock-invoke"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "InvokeBedrockRuntime"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
        ]
        Resource = "arn:aws:bedrock:${local.region}::foundation-model/${var.bedrock_foundation_model}"
      }
    ]
  })
}
