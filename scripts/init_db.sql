-- ============================================================================
-- MULTI-TIER AGENT ECOSYSTEM - DATABASE INITIALIZATION
-- ============================================================================
-- This script runs automatically when PostgreSQL container first starts
-- File: scripts/init_db.sql

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLE: checkpoints (LangGraph State Persistence)
-- ============================================================================

CREATE TABLE IF NOT EXISTS checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL,
    checkpoint_id VARCHAR(255) UNIQUE NOT NULL,
    state JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT checkpoints_workflow_id_not_empty CHECK (workflow_id::text != ''),
    CONSTRAINT checkpoints_checkpoint_id_not_empty CHECK (checkpoint_id != ''),
    CONSTRAINT checkpoints_state_not_empty CHECK (jsonb_typeof(state) = 'object')
);

-- Indexes for checkpoints
CREATE INDEX IF NOT EXISTS idx_checkpoints_workflow ON checkpoints(workflow_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_created ON checkpoints(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_checkpoints_checkpoint_id ON checkpoints(checkpoint_id);

-- Comments
COMMENT ON TABLE checkpoints IS 'LangGraph workflow state checkpoints for resumability';
COMMENT ON COLUMN checkpoints.workflow_id IS 'References workflows.id (foreign key enforced after workflows table)';
COMMENT ON COLUMN checkpoints.checkpoint_id IS 'Unique checkpoint identifier from LangGraph';
COMMENT ON COLUMN checkpoints.state IS 'Full WorkflowState schema as JSON';
COMMENT ON COLUMN checkpoints.metadata IS 'Additional metadata (agent, phase, token_usage)';

-- ============================================================================
-- TABLE: workflows (Workflow Execution Metadata)
-- ============================================================================

CREATE TABLE IF NOT EXISTS workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_request TEXT NOT NULL,
    status VARCHAR(50) NOT NULL,
    current_phase VARCHAR(50),
    current_agent VARCHAR(100),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT workflows_status_valid CHECK (status IN (
        'pending', 'running', 'paused', 'completed', 'failed', 'cancelled'
    )),
    CONSTRAINT workflows_phase_valid CHECK (current_phase IN (
        'planning', 'architecture', 'preparation', 'development', 'validation', 'delivery'
    ) OR current_phase IS NULL),
    CONSTRAINT workflows_completed_after_started CHECK (
        completed_at IS NULL OR completed_at >= started_at
    )
);

-- Indexes for workflows
CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status);
CREATE INDEX IF NOT EXISTS idx_workflows_started ON workflows(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_workflows_completed ON workflows(completed_at DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_workflows_current_phase ON workflows(current_phase);

-- Comments
COMMENT ON TABLE workflows IS 'High-level workflow execution tracking';
COMMENT ON COLUMN workflows.user_request IS 'Original user input that triggered workflow';
COMMENT ON COLUMN workflows.status IS 'Workflow lifecycle status';
COMMENT ON COLUMN workflows.current_phase IS 'Current tier/phase (tier_0 to tier_5)';
COMMENT ON COLUMN workflows.current_agent IS 'Currently executing agent name';
COMMENT ON COLUMN workflows.metadata IS 'Budget usage, rejection counts, quality gates';

-- ============================================================================
-- TABLE: audit_events (Compliance and Audit Trail)
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    agent VARCHAR(100),
    event_data JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT audit_event_type_not_empty CHECK (event_type != '')
);

-- Indexes for audit_events
CREATE INDEX IF NOT EXISTS idx_audit_workflow ON audit_events(workflow_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_events(agent);

-- Comments
COMMENT ON TABLE audit_events IS 'Immutable audit log for compliance and debugging';
COMMENT ON COLUMN audit_events.event_type IS 'Event category (e.g., agent.started, validation.rejected)';
COMMENT ON COLUMN audit_events.agent IS 'Agent that generated the event';
COMMENT ON COLUMN audit_events.event_data IS 'Event-specific data (file changes, errors, decisions)';

-- ============================================================================
-- TABLE: artifacts (Generated Code and Reports)
-- ============================================================================

CREATE TABLE IF NOT EXISTS artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    artifact_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    storage_location TEXT NOT NULL,
    size_bytes BIGINT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT artifacts_type_valid CHECK (artifact_type IN (
        'code', 'test', 'report', 'config', 'documentation', 'log'
    )),
    CONSTRAINT artifacts_size_positive CHECK (size_bytes >= 0)
);

-- Indexes for artifacts
CREATE INDEX IF NOT EXISTS idx_artifacts_workflow ON artifacts(workflow_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS idx_artifacts_created ON artifacts(created_at DESC);

-- Comments
COMMENT ON TABLE artifacts IS 'Registry of generated files stored in MinIO';
COMMENT ON COLUMN artifacts.artifact_type IS 'Category of generated artifact';
COMMENT ON COLUMN artifacts.file_path IS 'Relative path within project (e.g., src/main.py)';
COMMENT ON COLUMN artifacts.storage_location IS 'MinIO object key (bucket/prefix/filename)';
COMMENT ON COLUMN artifacts.size_bytes IS 'File size for storage tracking';

-- ============================================================================
-- TABLE: budget_tracking (Cost and Token Usage)
-- ============================================================================

CREATE TABLE IF NOT EXISTS budget_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    agent VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 6) DEFAULT 0.0,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT budget_tokens_positive CHECK (tokens_input >= 0 AND tokens_output >= 0),
    CONSTRAINT budget_cost_positive CHECK (cost_usd >= 0)
);

-- Indexes for budget_tracking
CREATE INDEX IF NOT EXISTS idx_budget_workflow ON budget_tracking(workflow_id);
CREATE INDEX IF NOT EXISTS idx_budget_agent ON budget_tracking(agent);
CREATE INDEX IF NOT EXISTS idx_budget_timestamp ON budget_tracking(timestamp DESC);

-- Comments
COMMENT ON TABLE budget_tracking IS 'Per-agent token usage and cost tracking';
COMMENT ON COLUMN budget_tracking.model IS 'LLM model used (e.g., gpt-4, claude-3-opus)';
COMMENT ON COLUMN budget_tracking.tokens_input IS 'Input tokens (prompt)';
COMMENT ON COLUMN budget_tracking.tokens_output IS 'Output tokens (completion)';
COMMENT ON COLUMN budget_tracking.cost_usd IS 'Calculated cost in USD';

-- ============================================================================
-- TABLE: quality_gates (Quality Gate Results)
-- ============================================================================

CREATE TABLE IF NOT EXISTS quality_gates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    gate_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    evaluated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    criteria JSONB DEFAULT '[]',
    results JSONB DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT quality_gate_status_valid CHECK (status IN ('passed', 'failed', 'skipped'))
);

-- Indexes for quality_gates
CREATE INDEX IF NOT EXISTS idx_quality_gates_workflow ON quality_gates(workflow_id);
CREATE INDEX IF NOT EXISTS idx_quality_gates_status ON quality_gates(status);
CREATE INDEX IF NOT EXISTS idx_quality_gates_evaluated ON quality_gates(evaluated_at DESC);

-- Comments
COMMENT ON TABLE quality_gates IS 'Quality gate evaluation results';
COMMENT ON COLUMN quality_gates.gate_name IS 'Gate identifier (tier_1_planning, tier_4_validation)';
COMMENT ON COLUMN quality_gates.criteria IS 'Evaluation criteria checklist';
COMMENT ON COLUMN quality_gates.results IS 'Detailed pass/fail results per criterion';

-- ============================================================================
-- FOREIGN KEY CONSTRAINTS
-- ============================================================================

-- Add foreign key to checkpoints (deferred from table creation)
ALTER TABLE checkpoints DROP CONSTRAINT IF EXISTS fk_checkpoints_workflow;
ALTER TABLE checkpoints ADD CONSTRAINT fk_checkpoints_workflow
    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE;

-- ============================================================================
-- MATERIALIZED VIEWS (Performance Optimization)
-- ============================================================================

-- Workflow summary with latest checkpoint
CREATE MATERIALIZED VIEW IF NOT EXISTS workflow_summary AS
SELECT 
    w.id,
    w.user_request,
    w.status,
    w.current_phase,
    w.current_agent,
    w.started_at,
    w.completed_at,
    COALESCE(
        EXTRACT(EPOCH FROM (w.completed_at - w.started_at))::INTEGER,
        EXTRACT(EPOCH FROM (NOW() - w.started_at))::INTEGER
    ) AS duration_seconds,
    (SELECT COUNT(*) FROM checkpoints c WHERE c.workflow_id = w.id) AS checkpoint_count,
    (SELECT MAX(created_at) FROM checkpoints c WHERE c.workflow_id = w.id) AS latest_checkpoint_at,
    (SELECT COALESCE(SUM(cost_usd), 0) FROM budget_tracking b WHERE b.workflow_id = w.id) AS total_cost_usd,
    (SELECT COALESCE(SUM(tokens_input + tokens_output), 0) FROM budget_tracking b WHERE b.workflow_id = w.id) AS total_tokens
FROM workflows w;

CREATE UNIQUE INDEX IF NOT EXISTS idx_workflow_summary_id ON workflow_summary(id);

COMMENT ON MATERIALIZED VIEW workflow_summary IS 'Aggregated workflow metrics for dashboard';

-- Refresh function (call periodically)
CREATE OR REPLACE FUNCTION refresh_workflow_summary()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY workflow_summary;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- CLEANUP FUNCTIONS
-- ============================================================================

-- Function: Delete old checkpoints for abandoned workflows
CREATE OR REPLACE FUNCTION cleanup_abandoned_checkpoints(retention_hours INTEGER DEFAULT 48)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM checkpoints
    WHERE workflow_id IN (
        SELECT id FROM workflows 
        WHERE status NOT IN ('running', 'paused')
    )
    AND created_at < NOW() - (retention_hours || ' hours')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_abandoned_checkpoints IS 'Delete checkpoints older than retention_hours for non-active workflows';

-- Function: Archive completed workflows
CREATE OR REPLACE FUNCTION archive_completed_workflows(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    -- Move to archive table (if exists)
    -- For now, just delete old completed workflows
    DELETE FROM workflows
    WHERE status = 'completed'
    AND completed_at < NOW() - (retention_days || ' days')::INTERVAL;
    
    GET DIAGNOSTICS archived_count = ROW_COUNT;
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION archive_completed_workflows IS 'Archive workflows older than retention_days';

-- ============================================================================
-- INITIAL DATA (Optional Test Data)
-- ============================================================================

-- Insert a sample workflow for testing (only if table is empty)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM workflows LIMIT 1) THEN
        INSERT INTO workflows (id, user_request, status, current_phase, current_agent, metadata)
        VALUES (
            gen_random_uuid(),
            'Test workflow: Create a simple FastAPI hello world app',
            'pending',
            NULL,
            NULL,
            '{"test_mode": true}'::jsonb
        );
    END IF;
END $$;

-- ============================================================================
-- GRANTS (Security)
-- ============================================================================

-- Grant permissions to agent_user
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO agent_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO agent_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO agent_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO agent_user;

-- Default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO agent_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO agent_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify tables created
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE'
    AND table_name IN ('checkpoints', 'workflows', 'audit_events', 'artifacts', 'budget_tracking', 'quality_gates');
    
    IF table_count = 6 THEN
        RAISE NOTICE '✅ All 6 tables created successfully';
    ELSE
        RAISE WARNING '⚠️  Expected 6 tables, found %', table_count;
    END IF;
END $$;

-- ============================================================================
-- INITIALIZATION COMPLETE
-- ============================================================================

-- Log initialization
INSERT INTO audit_events (workflow_id, event_type, agent, event_data)
VALUES (
    (SELECT id FROM workflows LIMIT 1),
    'database.initialized',
    'infrastructure_setup_agent',
    jsonb_build_object(
        'timestamp', NOW(),
        'tables_created', 6,
        'indexes_created', 15,
        'functions_created', 3
    )
);

RAISE NOTICE '============================================================================';
RAISE NOTICE 'DATABASE INITIALIZATION COMPLETE';
RAISE NOTICE '============================================================================';
RAISE NOTICE 'Tables:      checkpoints, workflows, audit_events, artifacts, budget_tracking, quality_gates';
RAISE NOTICE 'Views:       workflow_summary';
RAISE NOTICE 'Functions:   cleanup_abandoned_checkpoints, archive_completed_workflows, refresh_workflow_summary';
RAISE NOTICE '============================================================================';
