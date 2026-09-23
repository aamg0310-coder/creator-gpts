-- ==================== FIX VECTOR INSERT ====================
-- Función para insertar documentos con embeddings como vector proper

CREATE OR REPLACE FUNCTION insert_document_with_embedding(
  p_chatbot_id INTEGER,
  p_user_id UUID,
  p_filename TEXT,
  p_content TEXT,
  p_embedding JSON,  -- embedding as JSON array [0.1, 0.2, ...]
  p_chunk_index INTEGER,
  p_metadata JSONB DEFAULT '{}'
)
RETURNS TABLE (
  id BIGINT,
  chatbot_id INTEGER,
  user_id UUID,
  filename TEXT,
  content TEXT,
  embedding VECTOR(1536),
  chunk_index INTEGER,
  metadata JSONB,
  created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_embedding_vector VECTOR(1536);
BEGIN
  -- Convert JSON array to vector using array_to_string and ::vector
  -- JSON array [0.1, 0.2, ...] -> text '[0.1,0.2,...]' -> vector
  v_embedding_vector := ('[' || array_to_string(
    (SELECT jsonb_array_elements_text(p_embedding::jsonb) ORDER BY ordinality),
    ','
  ) || ']')::VECTOR(1536);
  
  RETURN QUERY
  INSERT INTO documents (chatbot_id, user_id, filename, content, embedding, chunk_index, metadata)
  VALUES (
    p_chatbot_id,
    p_user_id,
    p_filename,
    p_content,
    v_embedding_vector,
    p_chunk_index,
    p_metadata
  )
  RETURNING id, chatbot_id, user_id, filename, content, embedding, chunk_index, metadata, created_at;
END;
$$;

-- Grant execute to anon role (used by Edge Functions)
GRANT EXECUTE ON FUNCTION insert_document_with_embedding(INTEGER, UUID, TEXT, TEXT, JSON, INTEGER, JSONB) TO anon;