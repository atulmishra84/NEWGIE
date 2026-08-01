"""Orchestrator settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ORCH_", env_file=".env", extra="ignore")

    env: str = "local"
    host: str = "0.0.0.0"
    port: int = 8090
    staging_base_url: str = "http://localhost:8090"
    golden_staging_url: str = "http://localhost:8090/demo/golden"
    prod_base_url: str = "http://localhost:8090/demo/prod"
    context_intelligence_url: str = "http://context-intelligence:8080"
    risk_assessment_url: str = "http://risk-assessment:8091"
    policy_engine_url: str = "http://policy-engine:8092"
    prod_confirm_phrase: str = "approve production deploy"
    allow_customer_prod: bool = False
    unsupervised_prod: bool = False
    artifact_dir: str = "/tmp/gie-fleet-artifacts"
    multi_region_config: str = "/workspace/deploy/full-gie/multi-region.yaml"

    # Voice providers: stub | openai | deepgram
    stt_provider: str = "stub"
    tts_provider: str = "stub"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    deepgram_api_key: str = ""
    deepgram_base_url: str = "https://api.deepgram.com/v1"

    # CVE scanners: comma-separated osv,snyk
    cve_providers: str = "osv"
    snyk_token: str = ""
    snyk_org: str = ""
    osv_api_url: str = "https://api.osv.dev/v1/query"
    cve_manifest_path: str = ""
    cve_block_high: bool = False

    @property
    def cve_provider_list(self) -> list[str]:
        return [p.strip().lower() for p in self.cve_providers.split(",") if p.strip()]


settings = Settings()
