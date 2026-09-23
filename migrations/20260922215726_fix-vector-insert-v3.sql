-- ==================== FIX VECTOR INSERT V5 ====================
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
  v_embedding_text TEXT;
  v_embedding_vector VECTOR(1536);
  v_new_id BIGINT;
BEGIN
  -- Convert JSON array to comma-separated text: 0.1,0.2,...
  SELECT string_agg(elem, ',' ORDER BY ord) INTO v_embedding_text
  FROM jsonb_array_elements_text(p_embedding::jsonb) WITH ORDINALITY AS arr(elem, ord);
  
  -- Convert text representation to vector
  -- [0.1,0.2,...] -> vector
  INSERT INTO documents (chatbot_id, user_id, filename, content, embedding, chunk_index, metadata)
  VALUES (
    p_chatbot_id,
    p_user_id,
    p_filename,
    p_content,
    ('[' || v_embedding_text || ']')::VECTOR(1536),
    p_chunk_index,
    p_metadata
  )
  RETURNING documents.id, documents.chatbot_id, documents.user_id, documents.filename, 
            documents.content, documents.embedding, documents.chunk_index, 
            documents.metadata, documents.created_at
  INTO v_new_id, chatbot_id, user_id, filename, content, embedding, chunk_index, metadata, created_at;
  
  RETURN NEXT;
END;
$$;

-- Grant execute to anon role (used by Edge Functions)
GRANT EXECUTE ON FUNCTION insert_document_with_embedding(INTEGER, UUID, TEXT, TEXT, JSON, INTEGER, JSONB) TO anon;