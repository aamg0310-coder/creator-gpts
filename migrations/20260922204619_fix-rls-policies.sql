-- ==================== FIX RLS POLICIES ====================
-- Simplificar políticas: Django maneja permisos a nivel API
-- RLS solo protege contra acceso no autenticado a operaciones de escritura

-- 1. ELIMINAR POLÍTICAS EXISTENTES
DROP POLICY IF EXISTS "Users own docs" ON documents;
DROP POLICY IF EXISTS "Users insert docs" ON documents;
DROP POLICY IF EXISTS "Creator delete docs" ON documents;

-- 2. NUEVAS POLÍTICAS SIMPLES
-- SELECT: Permitir lectura a todos (Django verifica permisos en la API)
-- Esto permite que la Edge Function (usando anon_key) pueda leer documentos
CREATE POLICY "Documents readable" ON documents FOR SELECT
USING (true);

-- INSERT: Solo usuarios autenticados pueden insertar
CREATE POLICY "Documents insertable" ON documents FOR INSERT
WITH CHECK (auth.uid() IS NOT NULL);

-- DELETE: Solo usuarios autenticados pueden eliminar
CREATE POLICY "Documents deletable" ON documents FOR DELETE
USING (auth.uid() IS NOT NULL);

-- 3. POLÍTICAS PARA chat_session_memories (sin cambios - ya funcionan)
-- Estas usan user_id directamente ya que las sesiones son privadas por usuario
DROP POLICY IF EXISTS "Users own session memory" ON chat_session_memories;
DROP POLICY IF EXISTS "Users insert session memory" ON chat_session_memories;

CREATE POLICY "Users own session memory" ON chat_session_memories FOR SELECT
USING (user_id = auth.uid());

CREATE POLICY "Users insert session memory" ON chat_session_memories FOR INSERT
WITH CHECK (user_id = auth.uid());