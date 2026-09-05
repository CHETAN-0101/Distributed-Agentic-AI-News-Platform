-- =============================================================================
-- AgentOS — PostgreSQL Initialization
-- =============================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =============================================================================
-- TENANTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS tenants (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL UNIQUE,
    slug        TEXT NOT NULL UNIQUE,
    settings    JSONB NOT NULL DEFAULT '{}',
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO tenants (name, slug) VALUES ('Default', 'default') ON CONFLICT DO NOTHING;

-- =============================================================================
-- USERS
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email           TEXT NOT NULL,
    username        TEXT NOT NULL,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'operator', 'analyst', 'user', 'readonly')),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    preferences     JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, email)
);

CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- =============================================================================
-- AGENTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS agents (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id            TEXT NOT NULL UNIQUE,
    name                TEXT NOT NULL,
    description         TEXT,
    version             TEXT NOT NULL DEFAULT '1.0.0',
    status              TEXT NOT NULL DEFAULT 'initializing'
                            CHECK (status IN ('initializing', 'healthy', 'degraded', 'unhealthy', 'offline', 'circuit_open')),
    host                TEXT NOT NULL,
    port                INTEGER NOT NULL,
    capabilities        TEXT[] NOT NULL DEFAULT '{}',
    input_schema        JSONB,
    output_schema       JSONB,
    required_permissions TEXT[] NOT NULL DEFAULT '{}',
    metadata            JSONB NOT NULL DEFAULT '{}',
    reliability_score   FLOAT NOT NULL DEFAULT 1.0,
    avg_latency_ms      FLOAT,
    cost_estimate       FLOAT,
    last_heartbeat      TIMESTAMPTZ,
    registered_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_capabilities ON agents USING GIN(capabilities);

-- =============================================================================
-- AGENT HEALTH HISTORY
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_health_history (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id        TEXT NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    status          TEXT NOT NULL,
    latency_ms      FLOAT,
    error_rate      FLOAT,
    success_rate    FLOAT,
    queue_depth     INTEGER,
    details         JSONB,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_health_agent ON agent_health_history(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_health_time ON agent_health_history(recorded_at DESC);

-- =============================================================================
-- WORKFLOWS
-- =============================================================================
CREATE TABLE IF NOT EXISTS workflows (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    user_id         UUID REFERENCES users(id),
    name            TEXT NOT NULL,
    description     TEXT,
    status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'planning', 'running', 'paused', 'awaiting_approval',
                                          'completed', 'failed', 'cancelled', 'compensating')),
    priority        TEXT NOT NULL DEFAULT 'NORMAL' CHECK (priority IN ('LOW', 'NORMAL', 'HIGH', 'CRITICAL')),
    graph           JSONB NOT NULL DEFAULT '{}',
    input           JSONB,
    output          JSONB,
    error           JSONB,
    trace_id        TEXT,
    correlation_id  TEXT,
    idempotency_key TEXT UNIQUE,
    deadline        TIMESTAMPTZ,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workflows_tenant ON workflows(tenant_id);
CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status);
CREATE INDEX IF NOT EXISTS idx_workflows_created ON workflows(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_workflows_idempotency ON workflows(idempotency_key);

-- =============================================================================
-- WORKFLOW NODES
-- =============================================================================
CREATE TABLE IF NOT EXISTS workflow_nodes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id     UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    node_id         TEXT NOT NULL,
    agent_id        TEXT REFERENCES agents(agent_id),
    capability      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped',
                                          'awaiting_approval', 'cancelled', 'retrying')),
    input           JSONB,
    output          JSONB,
    error           JSONB,
    depends_on      TEXT[] NOT NULL DEFAULT '{}',
    retry_count     INTEGER NOT NULL DEFAULT 0,
    max_retries     INTEGER NOT NULL DEFAULT 3,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (workflow_id, node_id)
);

CREATE INDEX IF NOT EXISTS idx_wf_nodes_workflow ON workflow_nodes(workflow_id);
CREATE INDEX IF NOT EXISTS idx_wf_nodes_status ON workflow_nodes(status);

-- =============================================================================
-- TASKS
-- =============================================================================
CREATE TABLE IF NOT EXISTS tasks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    workflow_id     UUID REFERENCES workflows(id),
    workflow_node_id UUID REFERENCES workflow_nodes(id),
    agent_id        TEXT REFERENCES agents(agent_id),
    capability      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'assigned', 'running', 'completed', 'failed',
                                          'retrying', 'dead', 'cancelled')),
    priority        TEXT NOT NULL DEFAULT 'NORMAL',
    input           JSONB,
    output          JSONB,
    error           TEXT,
    confidence      FLOAT,
    evidence        JSONB,
    token_usage     JSONB,
    execution_ms    INTEGER,
    retry_count     INTEGER NOT NULL DEFAULT 0,
    max_retries     INTEGER NOT NULL DEFAULT 3,
    trace_id        TEXT,
    correlation_id  TEXT,
    idempotency_key TEXT UNIQUE,
    deadline        TIMESTAMPTZ,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tasks_tenant ON tasks(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tasks_workflow ON tasks(workflow_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(agent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_idempotency ON tasks(idempotency_key);

-- =============================================================================
-- MEMORY
-- =============================================================================
CREATE TABLE IF NOT EXISTS memory (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    agent_id        TEXT,
    memory_type     TEXT NOT NULL CHECK (memory_type IN ('working', 'episodic', 'semantic', 'procedural', 'evidence', 'reflection')),
    key             TEXT,
    content         TEXT NOT NULL,
    embedding       vector(1024),
    metadata        JSONB NOT NULL DEFAULT '{}',
    confidence      FLOAT NOT NULL DEFAULT 1.0,
    importance      FLOAT NOT NULL DEFAULT 0.5,
    access_count    INTEGER NOT NULL DEFAULT 0,
    last_accessed   TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    archived        BOOLEAN NOT NULL DEFAULT FALSE,
    source_task_id  UUID REFERENCES tasks(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memory_tenant ON memory(tenant_id);
CREATE INDEX IF NOT EXISTS idx_memory_type ON memory(memory_type);
CREATE INDEX IF NOT EXISTS idx_memory_agent ON memory(agent_id);
CREATE INDEX IF NOT EXISTS idx_memory_embedding ON memory USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_memory_expires ON memory(expires_at);

-- =============================================================================
-- EVIDENCE
-- =============================================================================
CREATE TABLE IF NOT EXISTS evidence (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    evidence_type   TEXT NOT NULL CHECK (evidence_type IN ('OBSERVATION', 'INFERENCE', 'ASSUMPTION', 'SUPPORTED_FACT', 'CONFLICTING_CLAIM', 'UNVERIFIED_CLAIM')),
    content         TEXT NOT NULL,
    source_url      TEXT,
    source_name     TEXT,
    source_type     TEXT,
    author          TEXT,
    published_at    TIMESTAMPTZ,
    retrieved_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    passage         TEXT,
    confidence      FLOAT NOT NULL DEFAULT 0.5,
    credibility     FLOAT,
    task_id         UUID REFERENCES tasks(id),
    agent_id        TEXT,
    model_used      TEXT,
    embedding       vector(1024),
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evidence_tenant ON evidence(tenant_id);
CREATE INDEX IF NOT EXISTS idx_evidence_type ON evidence(evidence_type);
CREATE INDEX IF NOT EXISTS idx_evidence_task ON evidence(task_id);
CREATE INDEX IF NOT EXISTS idx_evidence_embedding ON evidence USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);

-- =============================================================================
-- CLAIMS
-- =============================================================================
CREATE TABLE IF NOT EXISTS claims (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    event_id        UUID,
    article_id      UUID,
    text            TEXT NOT NULL,
    subject         TEXT,
    predicate       TEXT,
    object          TEXT,
    status          TEXT NOT NULL DEFAULT 'UNVERIFIED'
                        CHECK (status IN ('CONFIRMED', 'SUPPORTED', 'CONFLICTING', 'UNVERIFIED',
                                          'INSUFFICIENT_EVIDENCE', 'OPINION', 'CORRECTED', 'OUTDATED')),
    confidence      FLOAT NOT NULL DEFAULT 0.5,
    source_agent_id TEXT,
    evidence_ids    UUID[] DEFAULT '{}',
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_claims_tenant ON claims(tenant_id);
CREATE INDEX IF NOT EXISTS idx_claims_event ON claims(event_id);
CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);

-- =============================================================================
-- NEWS ARTICLES
-- =============================================================================
CREATE TABLE IF NOT EXISTS news_articles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    article_id      TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    content         TEXT,
    summary         TEXT,
    source          TEXT NOT NULL,
    source_type     TEXT NOT NULL DEFAULT 'news' CHECK (source_type IN ('official', 'news', 'institutional', 'social', 'rss')),
    author          TEXT,
    url             TEXT NOT NULL,
    language        TEXT NOT NULL DEFAULT 'en',
    category        TEXT,
    entities        JSONB NOT NULL DEFAULT '[]',
    published_at    TIMESTAMPTZ,
    updated_at_src  TIMESTAMPTZ,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    embedding       vector(1024),
    word_count      INTEGER,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_articles_tenant ON news_articles(tenant_id);
CREATE INDEX IF NOT EXISTS idx_articles_source ON news_articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_published ON news_articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_language ON news_articles(language);
CREATE INDEX IF NOT EXISTS idx_articles_embedding ON news_articles USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_articles_title_trgm ON news_articles USING GIN(title gin_trgm_ops);

-- =============================================================================
-- NEWS EVENTS (Story Clusters)
-- =============================================================================
CREATE TABLE IF NOT EXISTS news_events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    title           TEXT NOT NULL,
    description     TEXT,
    status          TEXT NOT NULL DEFAULT 'developing'
                        CHECK (status IN ('developing', 'active', 'resolved', 'corrected', 'archived')),
    category        TEXT,
    importance      FLOAT NOT NULL DEFAULT 0.5,
    entities        JSONB NOT NULL DEFAULT '[]',
    article_ids     UUID[] NOT NULL DEFAULT '{}',
    claim_ids       UUID[] NOT NULL DEFAULT '{}',
    timeline        JSONB NOT NULL DEFAULT '[]',
    embedding       vector(1024),
    first_seen      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_news_events_tenant ON news_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_news_events_status ON news_events(status);
CREATE INDEX IF NOT EXISTS idx_news_events_importance ON news_events(importance DESC);
CREATE INDEX IF NOT EXISTS idx_news_events_last_updated ON news_events(last_updated DESC);
CREATE INDEX IF NOT EXISTS idx_news_events_embedding ON news_events USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);

-- =============================================================================
-- APPROVAL REQUESTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS approval_requests (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    workflow_id     UUID REFERENCES workflows(id),
    task_id         UUID REFERENCES tasks(id),
    requested_by    TEXT NOT NULL,
    action          TEXT NOT NULL,
    risk_level      TEXT NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    reason          TEXT NOT NULL,
    evidence        JSONB NOT NULL DEFAULT '[]',
    proposed_change JSONB,
    rollback_plan   JSONB,
    status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'approved', 'rejected', 'expired', 'cancelled')),
    reviewer_id     UUID REFERENCES users(id),
    reviewer_note   TEXT,
    expires_at      TIMESTAMPTZ NOT NULL,
    reviewed_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_approvals_tenant ON approval_requests(tenant_id);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_approvals_workflow ON approval_requests(workflow_id);
CREATE INDEX IF NOT EXISTS idx_approvals_expires ON approval_requests(expires_at);

-- =============================================================================
-- POLICIES
-- =============================================================================
CREATE TABLE IF NOT EXISTS policies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    name            TEXT NOT NULL,
    description     TEXT,
    action_pattern  TEXT NOT NULL,
    conditions      JSONB NOT NULL DEFAULT '{}',
    risk_level      TEXT NOT NULL DEFAULT 'LOW' CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    requires_approval BOOLEAN NOT NULL DEFAULT FALSE,
    allowed_roles   TEXT[] NOT NULL DEFAULT '{}',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    priority        INTEGER NOT NULL DEFAULT 0,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, name)
);

CREATE INDEX IF NOT EXISTS idx_policies_tenant ON policies(tenant_id);
CREATE INDEX IF NOT EXISTS idx_policies_active ON policies(is_active);

-- =============================================================================
-- AUDIT LOG
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    actor_id        UUID REFERENCES users(id),
    actor_type      TEXT NOT NULL DEFAULT 'user' CHECK (actor_type IN ('user', 'agent', 'system')),
    action          TEXT NOT NULL,
    resource_type   TEXT,
    resource_id     TEXT,
    agent_id        TEXT,
    model_used      TEXT,
    tool_used       TEXT,
    input_hash      TEXT,
    output_hash     TEXT,
    workflow_id     UUID,
    task_id         UUID,
    policy_id       UUID,
    approval_id     UUID,
    result          TEXT CHECK (result IN ('success', 'failure', 'pending')),
    details         JSONB NOT NULL DEFAULT '{}',
    ip_address      TEXT,
    trace_id        TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit_log(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_workflow ON audit_log(workflow_id);

-- =============================================================================
-- EVALUATION RESULTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS evaluations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    task_id         UUID REFERENCES tasks(id),
    agent_id        TEXT NOT NULL,
    model_used      TEXT,
    eval_type       TEXT NOT NULL CHECK (eval_type IN ('groundedness', 'hallucination', 'correctness', 'relevance', 'completeness', 'cost')),
    score           FLOAT NOT NULL,
    predicted_confidence FLOAT,
    actual_correct  BOOLEAN,
    details         JSONB NOT NULL DEFAULT '{}',
    evaluator       TEXT NOT NULL DEFAULT 'system',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_eval_tenant ON evaluations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_eval_agent ON evaluations(agent_id);
CREATE INDEX IF NOT EXISTS idx_eval_type ON evaluations(eval_type);
CREATE INDEX IF NOT EXISTS idx_eval_created ON evaluations(created_at DESC);

-- =============================================================================
-- TOOLS
-- =============================================================================
CREATE TABLE IF NOT EXISTS tools (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL UNIQUE,
    description     TEXT,
    tool_type       TEXT NOT NULL,
    config          JSONB NOT NULL DEFAULT '{}',
    required_permissions TEXT[] NOT NULL DEFAULT '{}',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- USER PREFERENCES (NewsFlow personalization)
-- =============================================================================
CREATE TABLE IF NOT EXISTS user_news_preferences (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    interests       TEXT[] NOT NULL DEFAULT '{}',
    preferred_sources TEXT[] NOT NULL DEFAULT '{}',
    excluded_sources TEXT[] NOT NULL DEFAULT '{}',
    diversity_weight FLOAT NOT NULL DEFAULT 0.3,
    language        TEXT NOT NULL DEFAULT 'en',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id)
);

-- =============================================================================
-- TRIGGERS: updated_at auto-update
-- =============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'tenants', 'users', 'agents', 'workflows', 'workflow_nodes', 'tasks',
        'memory', 'evidence', 'claims', 'news_articles', 'news_events',
        'approval_requests', 'policies', 'tools', 'user_news_preferences'
    ] LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS trigger_updated_at_%I ON %I;
            CREATE TRIGGER trigger_updated_at_%I
                BEFORE UPDATE ON %I
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        ', t, t, t, t);
    END LOOP;
END;
$$;

-- =============================================================================
-- SEED: Default policies
-- =============================================================================
INSERT INTO policies (tenant_id, name, action_pattern, risk_level, requires_approval, allowed_roles, priority)
SELECT
    (SELECT id FROM tenants WHERE slug = 'default'),
    name, action_pattern, risk_level, requires_approval, allowed_roles::TEXT[], priority
FROM (VALUES
    ('critical-action-approval', 'delete.*|truncate.*|drop.*', 'CRITICAL', TRUE, '{"admin"}', 100),
    ('security-scan-approval', 'security.scan.*', 'HIGH', TRUE, '{"admin","operator"}', 90),
    ('finance-advice-block', 'finance.advice.*', 'HIGH', TRUE, '{"admin","analyst"}', 80),
    ('data-export-approval', 'data.export.*', 'MEDIUM', TRUE, '{"admin","operator","analyst"}', 70),
    ('general-read-allow', 'read.*|list.*|search.*', 'LOW', FALSE, '{"admin","operator","analyst","user","readonly"}', 10)
) AS seed(name, action_pattern, risk_level, requires_approval, allowed_roles, priority)
ON CONFLICT DO NOTHING;

-- Default admin user (password: agentos_admin — CHANGE IN PRODUCTION)
INSERT INTO users (tenant_id, email, username, password_hash, role)
SELECT
    (SELECT id FROM tenants WHERE slug = 'default'),
    'admin@agentos.local',
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeX9mGSWJTjV/R9a2',  -- bcrypt of 'agentos_admin'
    'admin'
ON CONFLICT DO NOTHING;
