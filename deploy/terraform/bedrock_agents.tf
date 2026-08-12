# ── GIE Bedrock Agents — one per service ──────────────────────────────────────
# Each agent uses the bedrock_agent module from modules/bedrock_agent.
# All agents share the same Lambda (gie-bedrock-agents-<env>) and IAM role.

locals {
  common_tags = merge(var.tags, {
    Project     = "GIE"
    Environment = var.environment
    ManagedBy   = "Terraform"
  })

  lambda_arn  = aws_lambda_function.gie_bedrock_agents.arn
  agent_role  = aws_iam_role.bedrock_agent.arn
}

# ── 1. Context Intelligence ────────────────────────────────────────────────────
module "context_intelligence" {
  source = "./modules/bedrock_agent"

  agent_name       = "gie-context-intelligence-${var.environment}"
  description      = "Scans and maintains contextual models for entities across the GIE ecosystem."
  instruction      = "You are the Context Intelligence agent. You scan entities to build context models, track findings over time, and provide diff views of model evolution. Always validate entity_id before acting."
  foundation_model = var.bedrock_foundation_model
  agent_role_arn   = local.agent_role
  lambda_arn       = local.lambda_arn
  environment      = var.environment
  tags             = local.common_tags

  action_groups = {
    ContextIntelligence = {
      description = "Context scanning and model management"
      functions = {
        start_context_scan = {
          description = "Initiate a context scan for an entity"
          parameters = {
            entity_id  = { type = "string", description = "Entity identifier", required = true }
            scan_type  = { type = "string", description = "Scan type: full or incremental", required = false }
          }
        }
        get_scan_status = {
          description = "Check the status of a running context scan"
          parameters = {
            scan_id = { type = "string", description = "Scan job identifier", required = true }
          }
        }
        list_context_findings = {
          description = "List context findings for an entity"
          parameters = {
            entity_id = { type = "string", description = "Entity identifier", required = true }
            limit     = { type = "integer", description = "Maximum results to return", required = false }
          }
        }
        get_context_model = {
          description = "Retrieve the current context model for an entity"
          parameters = {
            entity_id = { type = "string", description = "Entity identifier", required = true }
          }
        }
        diff_context_models = {
          description = "Compare two versions of a context model"
          parameters = {
            entity_id    = { type = "string", description = "Entity identifier", required = true }
            from_version = { type = "string", description = "Previous model version", required = false }
            to_version   = { type = "string", description = "Current model version", required = false }
          }
        }
      }
    }
  }
}

# ── 2. Knowledge Intelligence ──────────────────────────────────────────────────
module "knowledge_intelligence" {
  source = "./modules/bedrock_agent"

  agent_name       = "gie-knowledge-intelligence-${var.environment}"
  description      = "Manages the GIE knowledge graph: nodes, relationships, and semantic search."
  instruction      = "You are the Knowledge Intelligence agent. You upsert, retrieve, and search knowledge graph nodes. Use semantic search to find related concepts and maintain graph integrity."
  foundation_model = var.bedrock_foundation_model
  agent_role_arn   = local.agent_role
  lambda_arn       = local.lambda_arn
  environment      = var.environment
  tags             = local.common_tags

  action_groups = {
    KnowledgeIntelligence = {
      description = "Knowledge graph CRUD and semantic search"
      functions = {
        upsert_knowledge_node = {
          description = "Create or update a knowledge graph node"
          parameters = {
            node_id   = { type = "string", description = "Unique node identifier", required = true }
            node_type = { type = "string", description = "Node category (concept, entity, policy, etc.)", required = false }
            label     = { type = "string", description = "Human-readable node label", required = false }
          }
        }
        get_knowledge_node = {
          description = "Retrieve a knowledge graph node by ID"
          parameters = {
            node_id = { type = "string", description = "Node identifier", required = true }
          }
        }
        search_knowledge_graph = {
          description = "Semantic search across the knowledge graph"
          parameters = {
            query = { type = "string", description = "Search query", required = true }
            limit = { type = "integer", description = "Maximum results", required = false }
          }
        }
        delete_knowledge_node = {
          description = "Remove a node from the knowledge graph"
          parameters = {
            node_id = { type = "string", description = "Node identifier", required = true }
          }
        }
        list_knowledge_nodes = {
          description = "List knowledge graph nodes by type"
          parameters = {
            node_type = { type = "string", description = "Filter by node type", required = false }
            limit     = { type = "integer", description = "Maximum results", required = false }
          }
        }
      }
    }
  }
}

# ── 3. Risk Intelligence ───────────────────────────────────────────────────────
module "risk_intelligence" {
  source = "./modules/bedrock_agent"

  agent_name       = "gie-risk-intelligence-${var.environment}"
  description      = "Calculates, recalculates, and reports risk scores for GIE entities."
  instruction      = "You are the Risk Intelligence agent. Calculate risk scores, identify risk factors, and produce risk reports. Always explain your risk assessment in terms of contributing factors."
  foundation_model = var.bedrock_foundation_model
  agent_role_arn   = local.agent_role
  lambda_arn       = local.lambda_arn
  environment      = var.environment
  tags             = local.common_tags

  action_groups = {
    RiskIntelligence = {
      description = "Risk scoring, reporting, and threshold management"
      functions = {
        calculate_risk_score = {
          description = "Calculate a risk score for an entity"
          parameters = {
            entity_id = { type = "string", description = "Entity identifier", required = true }
            risk_type = { type = "string", description = "Risk category (operational, financial, compliance, etc.)", required = false }
          }
        }
        recalculate_risk = {
          description = "Force recalculation of risk score using latest data"
          parameters = {
            entity_id = { type = "string", description = "Entity identifier", required = true }
          }
        }
        get_risk_report = {
          description = "Retrieve a risk report for an entity"
          parameters = {
            entity_id = { type = "string", description = "Entity identifier", required = true }
          }
        }
        list_risk_factors = {
          description = "List known risk factors for a risk type"
          parameters = {
            risk_type = { type = "string", description = "Risk category to list factors for", required = false }
          }
        }
        set_risk_threshold = {
          description = "Set acceptable risk threshold for an entity"
          parameters = {
            entity_id = { type = "string", description = "Entity identifier", required = true }
            threshold = { type = "number", description = "Risk threshold value (0.0–1.0)", required = true }
          }
        }
      }
    }
  }
}

# ── 4. Policy Intelligence ─────────────────────────────────────────────────────
module "policy_intelligence" {
  source = "./modules/bedrock_agent"

  agent_name       = "gie-policy-intelligence-${var.environment}"
  description      = "Evaluates policies, resolves decisions, and audits policy access for GIE subjects."
  instruction      = "You are the Policy Intelligence agent. Evaluate access policies, list applicable policies for a subject/resource pair, retrieve historical decisions, and audit policy usage."
  foundation_model = var.bedrock_foundation_model
  agent_role_arn   = local.agent_role
  lambda_arn       = local.lambda_arn
  environment      = var.environment
  tags             = local.common_tags

  action_groups = {
    PolicyIntelligence = {
      description = "Policy evaluation and decision management"
      functions = {
        evaluate_policy = {
          description = "Evaluate whether a subject can perform an action on a resource"
          parameters = {
            subject  = { type = "string", description = "Subject (user, service, role)", required = true }
            resource = { type = "string", description = "Resource ARN or identifier", required = true }
            action   = { type = "string", description = "Action to evaluate", required = false }
          }
        }
        list_applicable_policies = {
          description = "List all policies applicable to a subject/resource pair"
          parameters = {
            resource = { type = "string", description = "Resource identifier", required = true }
            role     = { type = "string", description = "Subject role", required = false }
          }
        }
        get_policy_decision = {
          description = "Retrieve a previously recorded policy decision"
          parameters = {
            decision_id = { type = "string", description = "Decision record identifier", required = true }
          }
        }
        audit_policy_access = {
          description = "Audit policy access history for a subject"
          parameters = {
            subject = { type = "string", description = "Subject to audit", required = true }
            since   = { type = "string", description = "ISO 8601 start timestamp", required = false }
          }
        }
        refresh_policy_cache = {
          description = "Flush and reload the policy cache"
          parameters = {
            scope = { type = "string", description = "Cache scope to flush: all, subject, resource", required = false }
          }
        }
      }
    }
  }
}

# ── 5. Compliance Intelligence ─────────────────────────────────────────────────
module "compliance_intelligence" {
  source = "./modules/bedrock_agent"

  agent_name       = "gie-compliance-intelligence-${var.environment}"
  description      = "Analyzes entity compliance against regulatory frameworks and flags violations."
  instruction      = "You are the Compliance Intelligence agent. Analyze entities against compliance frameworks (SOC2, ISO27001, GDPR, HIPAA). Flag violations with appropriate severity and produce compliance reports."
  foundation_model = var.bedrock_foundation_model
  agent_role_arn   = local.agent_role
  lambda_arn       = local.lambda_arn
  environment      = var.environment
  tags             = local.common_tags

  action_groups = {
    ComplianceIntelligence = {
      description = "Compliance analysis, validation, and violation management"
      functions = {
        analyze_compliance = {
          description = "Run a compliance analysis for an entity against a framework"
          parameters = {
            entity_id = { type = "string", description = "Entity identifier", required = true }
            framework = { type = "string", description = "Compliance framework (SOC2, GDPR, HIPAA, ISO27001)", required = false }
          }
        }
        validate_compliance = {
          description = "Validate an entity against a specific compliance rule"
          parameters = {
            entity_id = { type = "string", description = "Entity identifier", required = true }
            rule_id   = { type = "string", description = "Compliance rule identifier", required = true }
          }
        }
        get_compliance_report = {
          description = "Retrieve a compliance report for an entity"
          parameters = {
            entity_id = { type = "string", description = "Entity identifier", required = true }
          }
        }
        list_compliance_rules = {
          description = "List compliance rules for a framework"
          parameters = {
            framework = { type = "string", description = "Compliance framework name", required = false }
          }
        }
        flag_compliance_violation = {
          description = "Flag a compliance violation for an entity"
          parameters = {
            entity_id = { type = "string", description = "Entity identifier", required = true }
            rule_id   = { type = "string", description = "Violated rule identifier", required = true }
            severity  = { type = "string", description = "Violation severity: CRITICAL, HIGH, MEDIUM, LOW", required = false }
          }
        }
      }
    }
  }
}

# ── 6. Recommendation Intelligence ────────────────────────────────────────────
module "recommendation_intelligence" {
  source = "./modules/bedrock_agent"

  agent_name       = "gie-recommendation-intelligence-${var.environment}"
  description      = "Generates, reviews, and manages actionable recommendations for GIE entities."
  instruction      = "You are the Recommendation Intelligence agent. Generate contextual recommendations, manage their approval lifecycle, and retrieve historical recommendation data."
  foundation_model = var.bedrock_foundation_model
  agent_role_arn   = local.agent_role
  lambda_arn       = local.lambda_arn
  environment      = var.environment
  tags             = local.common_tags

  action_groups = {
    RecommendationIntelligence = {
      description = "Recommendation generation and lifecycle management"
      functions = {
        generate_recommendations = {
          description = "Generate recommendations for an entity based on current context"
          parameters = {
            entity_id    = { type = "string", description = "Entity identifier", required = true }
            context_type = { type = "string", description = "Recommendation context (risk, compliance, policy)", required = false }
          }
        }
        approve_recommendation = {
          description = "Approve a pending recommendation"
          parameters = {
            recommendation_id = { type = "string", description = "Recommendation identifier", required = true }
            reviewer          = { type = "string", description = "Approving reviewer identifier", required = false }
          }
        }
        reject_recommendation = {
          description = "Reject a pending recommendation"
          parameters = {
            recommendation_id = { type = "string", description = "Recommendation identifier", required = true }
            reason            = { type = "string", description = "Rejection reason", required = false }
          }
        }
        get_recommendation = {
          description = "Retrieve a specific recommendation"
          parameters = {
            recommendation_id = { type = "string", description = "Recommendation identifier", required = true }
          }
        }
        list_recommendations = {
          description = "List recommendations for an entity"
          parameters = {
            entity_id = { type = "string", description = "Entity identifier", required = true }
            status    = { type = "string", description = "Filter by status: PENDING, APPROVED, REJECTED", required = false }
            limit     = { type = "integer", description = "Maximum results", required = false }
          }
        }
      }
    }
  }
}

# ── 7. Explainability Intelligence ────────────────────────────────────────────
module "explainability_intelligence" {
  source = "./modules/bedrock_agent"

  agent_name       = "gie-explainability-intelligence-${var.environment}"
  description      = "Provides human-readable explanations for GIE decisions, scores, and policy outcomes."
  instruction      = "You are the Explainability Intelligence agent. Explain AI-driven decisions, risk scores, and policy outcomes in clear language. Provide reasoning traces and list contributing factors."
  foundation_model = var.bedrock_foundation_model
  agent_role_arn   = local.agent_role
  lambda_arn       = local.lambda_arn
  environment      = var.environment
  tags             = local.common_tags

  action_groups = {
    ExplainabilityIntelligence = {
      description = "Decision and score explainability"
      functions = {
        explain_decision = {
          description = "Get a natural-language explanation for a GIE decision"
          parameters = {
            decision_id  = { type = "string", description = "Decision identifier", required = true }
            detail_level = { type = "string", description = "Explanation depth: summary or detailed", required = false }
          }
        }
        get_reasoning_trace = {
          description = "Retrieve the step-by-step reasoning trace for a decision"
          parameters = {
            trace_id = { type = "string", description = "Reasoning trace identifier", required = true }
          }
        }
        explain_risk_score = {
          description = "Explain why an entity received a specific risk score"
          parameters = {
            entity_id = { type = "string", description = "Entity identifier", required = true }
            score     = { type = "number", description = "Risk score to explain", required = false }
          }
        }
        explain_policy_outcome = {
          description = "Explain why a policy decision resulted in a specific outcome"
          parameters = {
            policy_id = { type = "string", description = "Policy identifier", required = true }
            outcome   = { type = "string", description = "Policy outcome (ALLOW or DENY)", required = false }
          }
        }
        list_explanations = {
          description = "List available explanations for an entity"
          parameters = {
            entity_id = { type = "string", description = "Entity identifier", required = true }
            limit     = { type = "integer", description = "Maximum results", required = false }
          }
        }
      }
    }
  }
}

# ── 8. Validation Intelligence ────────────────────────────────────────────────
module "validation_intelligence" {
  source = "./modules/bedrock_agent"

  agent_name       = "gie-validation-intelligence-${var.environment}"
  description      = "Validates entities against schemas and runs simulation scenarios."
  instruction      = "You are the Validation Intelligence agent. Validate entities against defined schemas, run scenario simulations, and execute validation test suites."
  foundation_model = var.bedrock_foundation_model
  agent_role_arn   = local.agent_role
  lambda_arn       = local.lambda_arn
  environment      = var.environment
  tags             = local.common_tags

  action_groups = {
    ValidationIntelligence = {
      description = "Entity validation and scenario simulation"
      functions = {
        validate_entity = {
          description = "Validate an entity against a schema"
          parameters = {
            entity_id = { type = "string", description = "Entity identifier", required = true }
            schema_id = { type = "string", description = "Validation schema identifier", required = false }
          }
        }
        simulate_scenario = {
          description = "Run a scenario simulation for an entity"
          parameters = {
            scenario_id = { type = "string", description = "Scenario identifier", required = true }
            parameters  = { type = "string", description = "JSON-encoded scenario parameters", required = false }
          }
        }
        get_validation_result = {
          description = "Retrieve a validation result by ID"
          parameters = {
            result_id = { type = "string", description = "Validation result identifier", required = true }
          }
        }
        list_validation_rules = {
          description = "List available validation rules"
          parameters = {
            category = { type = "string", description = "Rule category filter", required = false }
          }
        }
        run_validation_suite = {
          description = "Run a full validation suite for an entity"
          parameters = {
            suite_id  = { type = "string", description = "Validation suite identifier", required = true }
            entity_id = { type = "string", description = "Entity identifier", required = true }
          }
        }
      }
    }
  }
}

# ── 9. Learning Intelligence ───────────────────────────────────────────────────
module "learning_intelligence" {
  source = "./modules/bedrock_agent"

  agent_name       = "gie-learning-intelligence-${var.environment}"
  description      = "Ingests feedback, triggers model learning updates, and manages the learning lifecycle."
  instruction      = "You are the Learning Intelligence agent. Accept feedback events, trigger incremental model updates, manage learning job approvals, and report on learning outcomes."
  foundation_model = var.bedrock_foundation_model
  agent_role_arn   = local.agent_role
  lambda_arn       = local.lambda_arn
  environment      = var.environment
  tags             = local.common_tags

  action_groups = {
    LearningIntelligence = {
      description = "Feedback ingestion and model learning management"
      functions = {
        submit_feedback = {
          description = "Submit a feedback event to improve model accuracy"
          parameters = {
            entity_id     = { type = "string", description = "Entity identifier", required = true }
            feedback_type = { type = "string", description = "Feedback category (correction, confirmation, rating)", required = false }
            payload       = { type = "string", description = "Feedback payload (JSON string)", required = false }
          }
        }
        trigger_learning = {
          description = "Trigger a model learning update job"
          parameters = {
            model_id = { type = "string", description = "Model to update", required = false }
            scope    = { type = "string", description = "Learning scope: incremental or full", required = false }
          }
        }
        approve_learning_update = {
          description = "Approve a pending learning model update"
          parameters = {
            update_id = { type = "string", description = "Learning update identifier", required = true }
            approver  = { type = "string", description = "Approving user or service identifier", required = false }
          }
        }
        get_learning_status = {
          description = "Check the status of a learning job"
          parameters = {
            job_id = { type = "string", description = "Learning job identifier", required = true }
          }
        }
        list_feedback_events = {
          description = "List submitted feedback events for an entity"
          parameters = {
            entity_id = { type = "string", description = "Entity identifier", required = true }
            limit     = { type = "integer", description = "Maximum results", required = false }
          }
        }
      }
    }
  }
}

# ── 10. Integration Intelligence ──────────────────────────────────────────────
module "integration_intelligence" {
  source = "./modules/bedrock_agent"

  agent_name       = "gie-integration-intelligence-${var.environment}"
  description      = "Manages external system integrations: connections, syncs, webhooks, and auth."
  instruction      = "You are the Integration Intelligence agent. Connect external providers, synchronize data, handle incoming webhooks, and authenticate third-party integrations."
  foundation_model = var.bedrock_foundation_model
  agent_role_arn   = local.agent_role
  lambda_arn       = local.lambda_arn
  environment      = var.environment
  tags             = local.common_tags

  action_groups = {
    IntegrationIntelligence = {
      description = "External integration lifecycle management"
      functions = {
        connect_integration = {
          description = "Connect to an external provider"
          parameters = {
            provider = { type = "string", description = "Integration provider name", required = true }
            config   = { type = "string", description = "JSON-encoded connection configuration", required = false }
          }
        }
        sync_integration = {
          description = "Synchronize data from an integration"
          parameters = {
            integration_id = { type = "string", description = "Integration identifier", required = true }
            full_sync      = { type = "boolean", description = "Perform a full sync instead of incremental", required = false }
          }
        }
        handle_webhook = {
          description = "Process an incoming webhook event from an external provider"
          parameters = {
            provider   = { type = "string", description = "Webhook source provider", required = true }
            event_type = { type = "string", description = "Webhook event type", required = true }
            payload    = { type = "string", description = "JSON-encoded webhook payload", required = false }
          }
        }
        authenticate_integration = {
          description = "Authenticate an integration with OAuth or API key"
          parameters = {
            provider    = { type = "string", description = "Integration provider", required = true }
            credentials = { type = "string", description = "JSON-encoded credentials (encrypted)", required = false }
          }
        }
        list_integrations = {
          description = "List configured integrations"
          parameters = {
            status = { type = "string", description = "Filter by status: ACTIVE, INACTIVE, ERROR", required = false }
          }
        }
      }
    }
  }
}

# ── 11. Policy Generator ───────────────────────────────────────────────────────
module "policy_generator" {
  source = "./modules/bedrock_agent"

  agent_name       = "gie-policy-generator-${var.environment}"
  description      = "Generates, drafts, validates, and publishes GIE policies using LLM assistance."
  instruction      = "You are the Policy Generator agent. Generate policy drafts from requirements, validate them against GIE standards, and publish approved policies to the policy registry."
  foundation_model = var.bedrock_foundation_model
  agent_role_arn   = local.agent_role
  lambda_arn       = local.lambda_arn
  environment      = var.environment
  tags             = local.common_tags

  action_groups = {
    PolicyGenerator = {
      description = "AI-assisted policy generation and publication"
      functions = {
        generate_policy = {
          description = "Generate a policy draft from requirements"
          parameters = {
            policy_type  = { type = "string", description = "Policy type (access_control, data_retention, privacy, etc.)", required = false }
            context      = { type = "string", description = "Business context for the policy", required = false }
            requirements = { type = "string", description = "Specific policy requirements", required = false }
          }
        }
        validate_policy_draft = {
          description = "Validate a policy draft for correctness and completeness"
          parameters = {
            draft_id = { type = "string", description = "Policy draft identifier", required = true }
          }
        }
        publish_policy = {
          description = "Publish an approved policy draft to the active registry"
          parameters = {
            draft_id = { type = "string", description = "Policy draft identifier", required = true }
            approver = { type = "string", description = "Approving authority identifier", required = false }
          }
        }
        get_policy_draft = {
          description = "Retrieve a policy draft"
          parameters = {
            draft_id = { type = "string", description = "Policy draft identifier", required = true }
          }
        }
        list_policy_drafts = {
          description = "List policy drafts"
          parameters = {
            policy_type = { type = "string", description = "Filter by policy type", required = false }
            status      = { type = "string", description = "Filter by status: DRAFT, REVIEW, APPROVED", required = false }
            limit       = { type = "integer", description = "Maximum results", required = false }
          }
        }
      }
    }
  }
}

# ── 12. Orchestrator ──────────────────────────────────────────────────────────
module "orchestrator" {
  source = "./modules/bedrock_agent"

  agent_name       = "gie-orchestrator-${var.environment}"
  description      = "Manages GIE workflow orchestration: starts, monitors, and analyses multi-step workflows."
  instruction      = "You are the Orchestrator agent. Start and manage multi-step GIE workflows, monitor their progress, cancel stuck workflows, and analyze workflow performance."
  foundation_model = var.bedrock_foundation_model
  agent_role_arn   = local.agent_role
  lambda_arn       = local.lambda_arn
  environment      = var.environment
  tags             = local.common_tags

  action_groups = {
    Orchestrator = {
      description = "Workflow lifecycle and analysis"
      functions = {
        start_workflow = {
          description = "Start a new workflow for an entity"
          parameters = {
            workflow_type = { type = "string", description = "Workflow type (risk_review, compliance_check, etc.)", required = true }
            entity_id     = { type = "string", description = "Entity identifier", required = true }
          }
        }
        get_workflow_status = {
          description = "Check the current status of a workflow"
          parameters = {
            workflow_id = { type = "string", description = "Workflow identifier", required = true }
          }
        }
        cancel_workflow = {
          description = "Cancel a running workflow"
          parameters = {
            workflow_id = { type = "string", description = "Workflow identifier", required = true }
            reason      = { type = "string", description = "Cancellation reason", required = false }
          }
        }
        analyze_workflow = {
          description = "Analyze a completed workflow for bottlenecks and improvements"
          parameters = {
            workflow_id = { type = "string", description = "Workflow identifier", required = true }
          }
        }
        list_workflows = {
          description = "List workflows, optionally filtered by status"
          parameters = {
            status = { type = "string", description = "Filter by status: RUNNING, COMPLETED, FAILED, CANCELLED", required = false }
            limit  = { type = "integer", description = "Maximum results", required = false }
          }
        }
      }
    }
  }
}

# ── 13. Chief Orchestrator ────────────────────────────────────────────────────
module "chief_orchestrator" {
  source = "./modules/bedrock_agent"

  agent_name       = "gie-chief-orchestrator-${var.environment}"
  description      = "Top-level orchestrator: dispatches tasks to sub-agents, aggregates results, and provides CVE scanning and voice synthesis."
  instruction      = "You are the Chief Orchestrator, the top-level GIE agent. Dispatch tasks to specialized sub-agents, aggregate their results into a unified answer, scan packages for CVE vulnerabilities, and synthesize voice responses."
  foundation_model = var.bedrock_foundation_model
  agent_role_arn   = local.agent_role
  lambda_arn       = local.lambda_arn
  environment      = var.environment
  tags             = local.common_tags

  action_groups = {
    ChiefOrchestrator = {
      description = "Multi-agent dispatch, aggregation, CVE scanning, and voice"
      functions = {
        dispatch_agent_task = {
          description = "Dispatch a task to a specialized GIE sub-agent"
          parameters = {
            agent_name = { type = "string", description = "Target agent name", required = true }
            task       = { type = "string", description = "Task description or JSON payload", required = true }
            priority   = { type = "string", description = "Task priority: LOW, NORMAL, HIGH, CRITICAL", required = false }
          }
        }
        get_agent_registry = {
          description = "List all registered GIE agents and their capabilities"
          parameters = {
            include_inactive = { type = "boolean", description = "Include inactive agents", required = false }
          }
        }
        aggregate_agent_results = {
          description = "Aggregate results from multiple sub-agent dispatches into a unified response"
          parameters = {
            session_id = { type = "string", description = "Orchestration session identifier", required = true }
          }
        }
        scan_cve = {
          description = "Scan a package for known CVE vulnerabilities"
          parameters = {
            package = { type = "string", description = "Package name to scan", required = true }
            version = { type = "string", description = "Package version", required = false }
          }
        }
        synthesize_voice_response = {
          description = "Convert a text response to speech audio"
          parameters = {
            text     = { type = "string", description = "Text to synthesize", required = true }
            voice_id = { type = "string", description = "Voice identifier for synthesis", required = false }
          }
        }
      }
    }
  }
}

# ── 14. Policy Engine ─────────────────────────────────────────────────────────
module "policy_engine" {
  source = "./modules/bedrock_agent"

  agent_name       = "gie-policy-engine-${var.environment}"
  description      = "Executes, registers, tests, and manages the lifecycle of GIE access-control policies."
  instruction      = "You are the Policy Engine agent. Execute policy rules in real-time, register new policies into the engine, run policy tests, and manage policy activation state."
  foundation_model = var.bedrock_foundation_model
  agent_role_arn   = local.agent_role
  lambda_arn       = local.lambda_arn
  environment      = var.environment
  tags             = local.common_tags

  action_groups = {
    PolicyEngine = {
      description = "Real-time policy execution and registry management"
      functions = {
        execute_policy = {
          description = "Execute a policy rule for a subject/resource pair"
          parameters = {
            policy_id = { type = "string", description = "Policy identifier", required = true }
            subject   = { type = "string", description = "Subject requesting access", required = true }
            resource  = { type = "string", description = "Resource being accessed", required = false }
          }
        }
        register_policy = {
          description = "Register a new policy into the engine"
          parameters = {
            policy_name    = { type = "string", description = "Unique policy name", required = true }
            policy_content = { type = "string", description = "Policy definition (Rego, JSON, or YAML)", required = true }
            policy_type    = { type = "string", description = "Policy type: ABAC, RBAC, ReBAC", required = false }
          }
        }
        deactivate_policy = {
          description = "Deactivate a policy in the engine"
          parameters = {
            policy_id = { type = "string", description = "Policy identifier", required = true }
          }
        }
        test_policy = {
          description = "Test a policy against a test case"
          parameters = {
            policy_id = { type = "string", description = "Policy identifier", required = true }
            test_case = { type = "string", description = "JSON-encoded test case (subject, resource, action)", required = true }
          }
        }
        list_active_policies = {
          description = "List all active policies in the engine"
          parameters = {
            policy_type = { type = "string", description = "Filter by policy type", required = false }
            limit       = { type = "integer", description = "Maximum results", required = false }
          }
        }
      }
    }
  }
}

# ── 15. Risk Assessment ────────────────────────────────────────────────────────
module "risk_assessment" {
  source = "./modules/bedrock_agent"

  agent_name       = "gie-risk-assessment-${var.environment}"
  description      = "Performs structured risk assessments, compares them over time, and schedules recurring evaluations."
  instruction      = "You are the Risk Assessment agent. Conduct structured risk assessments for entities, generate detailed reports, compare assessments across time periods, and schedule recurring assessments."
  foundation_model = var.bedrock_foundation_model
  agent_role_arn   = local.agent_role
  lambda_arn       = local.lambda_arn
  environment      = var.environment
  tags             = local.common_tags

  action_groups = {
    RiskAssessment = {
      description = "Structured risk assessment and scheduling"
      functions = {
        assess_risk = {
          description = "Perform a risk assessment for an entity"
          parameters = {
            entity_id       = { type = "string", description = "Entity identifier", required = true }
            assessment_type = { type = "string", description = "Assessment type: quick, standard, comprehensive", required = false }
          }
        }
        get_assessment_report = {
          description = "Retrieve a completed risk assessment report"
          parameters = {
            assessment_id = { type = "string", description = "Assessment identifier", required = true }
          }
        }
        compare_assessments = {
          description = "Compare two risk assessments to identify changes"
          parameters = {
            assessment_id_a = { type = "string", description = "First assessment identifier", required = true }
            assessment_id_b = { type = "string", description = "Second assessment identifier", required = true }
          }
        }
        schedule_assessment = {
          description = "Schedule recurring risk assessments for an entity"
          parameters = {
            entity_id = { type = "string", description = "Entity identifier", required = true }
            schedule  = { type = "string", description = "Schedule frequency: daily, weekly, monthly", required = false }
          }
        }
        list_assessments = {
          description = "List risk assessments for an entity"
          parameters = {
            entity_id = { type = "string", description = "Entity identifier", required = true }
            limit     = { type = "integer", description = "Maximum results", required = false }
          }
        }
      }
    }
  }
}
