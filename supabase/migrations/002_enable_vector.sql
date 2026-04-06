-- Enable pgvector extension and create scan embeddings table
-- Requires Supabase project with pgvector enabled

CREATE EXTENSION IF NOT EXISTS vector;

-- ─── Scan Embeddings ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scan_embeddings (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id      UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    embedding   vector(384),  -- all-MiniLM-L6-v2 produces 384-dim vectors
    metadata    JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scan_embeddings_job ON scan_embeddings(job_id);

-- IVFFlat index for approximate nearest neighbor search
-- Requires at least 100 rows to train; adjust lists based on dataset size
CREATE INDEX IF NOT EXISTS idx_scan_embeddings_vector
    ON scan_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ─── Semantic Search Function ──────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION match_scan_embeddings(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.8,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    job_id UUID,
    metadata JSONB,
    similarity float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        se.id,
        se.job_id,
        se.metadata,
        1 - (se.embedding <=> query_embedding) AS similarity
    FROM scan_embeddings se
    WHERE 1 - (se.embedding <=> query_embedding) > match_threshold
    ORDER BY se.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- RLS for embeddings table
ALTER TABLE scan_embeddings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all" ON scan_embeddings FOR ALL TO service_role USING (true) WITH CHECK (true);
