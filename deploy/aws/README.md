# GIE Bedrock Agents — AWS Lambda Handlers

## Structure

```
deploy/aws/
└── lambda_handlers/
    ├── shared.py                            # parse_event / ok / err utilities
    ├── dispatcher.py                        # Routes by actionGroup to per-agent handler
    ├── context_intelligence_handler.py
    ├── knowledge_intelligence_handler.py
    ├── risk_intelligence_handler.py
    ├── policy_intelligence_handler.py
    ├── compliance_intelligence_handler.py
    ├── recommendation_intelligence_handler.py
    ├── explainability_intelligence_handler.py
    ├── validation_intelligence_handler.py
    ├── learning_intelligence_handler.py
    ├── integration_intelligence_handler.py
    ├── policy_generator_handler.py
    ├── orchestrator_handler.py
    ├── chief_orchestrator_handler.py
    ├── policy_engine_handler.py
    └── risk_assessment_handler.py
```

## Deploy

No build step required. Terraform's `archive_file` data source zips the
`lambda_handlers/` directory automatically at plan/apply time.

```bash
cd deploy/terraform
terraform init
terraform plan -var="environment=dev"
terraform apply -var="environment=dev"
```

## Adding a New Agent

1. Create `lambda_handlers/<agent_name>_handler.py` with a `lambda_handler(event, context)` function.
2. Add the mapping in `dispatcher.py` under `_ACTION_GROUP_MAP`.
3. Add a new `module "<agent_name>"` block in `terraform/bedrock_agents.tf`.
4. Add the output entry in `terraform/bedrock_agents_outputs.tf`.
5. Run `terraform apply` — the zip is rebuilt automatically.
