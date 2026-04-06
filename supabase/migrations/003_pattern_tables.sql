-- Pattern tables and agent memory storage for Aegis Phase 2

-- ─── Injection Patterns ────────────────────────────────────────────────────────
-- Known attack patterns for semantic matching and ML training
CREATE TABLE IF NOT EXISTS injection_patterns (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pattern     TEXT NOT NULL,
    pattern_type TEXT NOT NULL DEFAULT 'regex' CHECK (pattern_type IN ('regex', 'semantic', 'embedding')),
    risk_level  TEXT NOT NULL DEFAULT 'medium' CHECK (risk_level IN ('safe', 'low', 'medium', 'high', 'critical')),
    confidence  FLOAT NOT NULL DEFAULT 0.8 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    source      TEXT, -- 'manual', 'ml-generated', 'user-feedback'
    metadata    JSONB NOT NULL DEFAULT '{}',
    hit_count   INTEGER NOT NULL DEFAULT 0,
    last_seen_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_injection_patterns_type ON injection_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_injection_patterns_risk ON injection_patterns(risk_level);
CREATE INDEX IF NOT EXISTS idx_injection_patterns_hit ON injection_patterns(hit_count DESC);

-- ─── Domain Patterns ───────────────────────────────────────────────────────────
-- Domain-specific rules and allow/block lists
CREATE TABLE IF NOT EXISTS domain_patterns (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain      TEXT NOT NULL,
    pattern_type TEXT NOT NULL CHECK (pattern_type IN ('allow', 'block', 'warn', 'require_review')),
    pattern     TEXT NOT NULL,
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT true,
    priority    INTEGER NOT NULL DEFAULT 100, -- Lower = higher priority
    metadata    JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_domain_patterns_domain ON domain_patterns(domain);
CREATE INDEX IF NOT EXISTS idx_domain_patterns_active ON domain_patterns(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_domain_patterns_priority ON domain_patterns(priority);

-- ─── Agent Memories ────────────────────────────────────────────────────────────
-- Persistent storage for agent memory consolidation
CREATE TABLE IF NOT EXISTS aegis_agent_memories (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name  TEXT NOT NULL,
    user_id     TEXT NOT NULL DEFAULT 'aegis-system',
    memory_type TEXT NOT NULL DEFAULT 'episodic' CHECK (memory_type IN ('episodic', 'semantic', 'procedural')),
    content     TEXT NOT NULL,
    embedding   vector(384), -- Same dimension as scan_embeddings (all-MiniLM-L6-v2)
    metadata    JSONB NOT NULL DEFAULT '{}',
    importance_score FLOAT DEFAULT 1.0,
    access_count INTEGER NOT NULL DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    expires_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_memories_agent ON aegis_agent_memories(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_memories_user ON aegis_agent_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_memories_type ON aegis_agent_memories(memory_type);

-- IVFFlat index for semantic search on agent memories
CREATE INDEX IF NOT EXISTS idx_agent_memories_vector
    ON aegis_agent_memories
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ─── Semantic Search Function for Agent Memories ───────────────────────────────
CREATE OR REPLACE FUNCTION match_agent_memories(
    query_embedding vector(384),
    agent_filter TEXT DEFAULT NULL,
    match_threshold float DEFAULT 0.8,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    agent_name TEXT,
    content TEXT,
    metadata JSONB,
    similarity float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        am.id,
        am.agent_name,
        am.content,
        am.metadata,
        1 - (am.embedding <=> query_embedding) AS similarity
    FROM aegis_agent_memories am
    WHERE 1 - (am.embedding <=> query_embedding) > match_threshold
        AND (agent_filter IS NULL OR am.agent_name = agent_filter)
        AND (am.expires_at IS NULL OR am.expires_at > NOW())
    ORDER BY am.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- ─── Session Scan Aggregation Function ─────────────────────────────────────────
CREATE OR REPLACE FUNCTION get_session_stats(session_uuid UUID)
RETURNS TABLE (
    total_scans BIGINT,
    injections_detected BIGINT,
    avg_risk_score FLOAT,
    max_risk_score FLOAT
)
LANGUAGE sql STABLE
AS $$
    SELECT
        COUNT(*)::BIGINT as total_scans,
        COUNT(*) FILTER (WHERE (result->>'is_injection')::boolean = true)::BIGINT as injections_detected,
        COALESCE(AVG((result->>'risk_score')::float), 0.0) as avg_risk_score,
        COALESCE(MAX((result->>'risk_score')::float), 0.0) as max_risk_score
    FROM jobs
    WHERE session_id = session_uuid;
$$;

-- ─── Row Level Security ────────────────────────────────────────────────────────
ALTER TABLE injection_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE domain_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE aegis_agent_memories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all" ON injection_patterns FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON domain_patterns FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON aegis_agent_memories FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ─── Trigger for updated_at ────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_injection_patterns_updated_at
    BEFORE UPDATE ON injection_patterns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_domain_patterns_updated_at
    BEFORE UPDATE ON domain_patterns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
