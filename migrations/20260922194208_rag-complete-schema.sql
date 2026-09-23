-- ==================== MIGRACIÓN RAG COMPLETA ====================
-- Habilita pgvector, crea tabla documents, match_documents y chat_session_memories

-- 1. HABILITAR EXTENSIÓN PGVECTOR
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. TABLA DE DOCUMENTOS RAG
CREATE TABLE IF NOT EXISTS documents (
  id BIGSERIAL PRIMARY KEY,
  chatbot_id INTEGER NOT NULL,
  user_id UUID NOT NULL,
  filename TEXT NOT NULL,
  content TEXT NOT NULL,
  embedding VECTOR(1536),
  chunk_index INTEGER DEFAULT 0,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para búsqueda semántica
CREATE INDEX IF NOT EXISTS idx_documents_chatbot ON documents (chatbot_id);
CREATE INDEX IF NOT EXISTS idx_documents_user ON documents (user_id);
CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING hnsw (embedding vector_cosine_ops);

-- 3. FUNCIÓN match_documents - BÚSQUEDA SEMÁNTICA
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding VECTOR(1536),
  match_chatbot_id INTEGER,
  match_count INT DEFAULT 5,
  match_threshold FLOAT DEFAULT 0.5
)
RETURNS TABLE (id BIGINT, content TEXT, similarity FLOAT, filename TEXT, chunk_index INTEGER)
LANGUAGE SQL STABLE
AS $$
  SELECT 
    d.id, 
    d.content, 
    1 - (d.embedding <=> query_embedding) AS similarity,
    d.filename,
    d.chunk_index
  FROM documents d
  WHERE d.chatbot_id = match_chatbot_id
    AND 1 - (d.embedding <=> query_embedding) > match_threshold
  ORDER BY d.embedding <=> query_embedding
  LIMIT match_count;
$$;

-- 4. TABLA DE MEMORIA DE SESIÓN (per-user conversation history)
CREATE TABLE IF NOT EXISTS chat_session_memories (
  id BIGSERIAL PRIMARY KEY,
  session_id UUID NOT NULL,
  user_id UUID NOT NULL,
  role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índice para recuperación ordenada
CREATE INDEX IF NOT EXISTS idx_session_memories_session ON chat_session_memories (session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_session_memories_user ON chat_session_memories (user_id);

-- 5. POLÍTICAS RLS (Row Level Security) - SEGURIDAD
-- Habilitar RLS en ambas tablas
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_session_memories ENABLE ROW LEVEL SECURITY;

-- Documentos: usuarios solo leen sus propios documentos (filtrando por user_id)
DROP POLICY IF EXISTS "Users own docs" ON documents;
CREATE POLICY "Users own docs" ON documents FOR SELECT 
USING (user_id = auth.uid());

-- Documentos: usuarios solo pueden insertar sus propios documentos
DROP POLICY IF EXISTS "Users insert docs" ON documents;
CREATE POLICY "Users insert docs" ON documents FOR INSERT WITH CHECK 
(user_id = auth.uid());

-- Documentos: usuarios solo pueden eliminar sus propios documentos
DROP POLICY IF EXISTS "Creator delete docs" ON documents;
CREATE POLICY "Creator delete docs" ON documents FOR DELETE 
USING (user_id = auth.uid());

-- Memoria de sesión: usuarios solo leen su propia memoria
DROP POLICY IF EXISTS "Users own session memory" ON chat_session_memories;
CREATE POLICY "Users own session memory" ON chat_session_memories FOR SELECT 
USING (user_id = auth.uid());

-- Memoria de sesión: usuarios pueden insertar su propia memoria
DROP POLICY IF EXISTS "Users insert session memory" ON chat_session_memories;
CREATE POLICY "Users insert session memory" ON chat_session_memories FOR INSERT 
WITH CHECK (user_id = auth.uid());