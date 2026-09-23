import { createClient } from "npm:@insforge/sdk";
import OpenAI from "npm:openai";

// Client con Model Gateway de InsForge (no requiere OPENROUTER_API_KEY si usas el gateway gestionado)
// Si tienes OPENROUTER_API_KEY, úsalo directamente; si no, usa el gateway de InsForge
const openai = new OpenAI({
  baseURL: Deno.env.get("INSFORGE_MODEL_GATEWAY_URL") || "https://openrouter.ai/api/v1",
  apiKey: Deno.env.get("OPENROUTER_API_KEY") || Deno.env.get("INSFORGE_MODEL_GATEWAY_KEY"),
  defaultHeaders: {
    "HTTP-Referer": Deno.env.get("APP_URL") || "https://chatbot-creator.local",
    "X-Title": "Chatbot Creator RAG",
  },
});

const insforge = createClient({
  baseUrl: Deno.env.get("INSFORGE_BASE_URL"),
  anonKey: Deno.env.get("INSFORGE_ANON_KEY"),
});

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS, DELETE",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

function splitContent(content: string, chunkSize = 500, overlap = 50): string[] {
  const chunks: string[] = [];
  let start = 0;
  while (start < content.length) {
    chunks.push(content.slice(start, start + chunkSize));
    start += chunkSize - overlap; // 450 chars overlap para coherencia semántica
  }
  return chunks;
}

export default async function handler(req: Request): Promise<Response> {
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders });

  try {
    const body = await req.json();
    const { action, chatbot_id, filename, content, query, top_k = 5, user_id } = body;

    switch (action) {
      case "upload": {
        if (!content || !filename) return new Response(JSON.stringify({ error: "content + filename required" }), { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } });

        const chunks = splitContent(content, 500, 50);
        const emb = await openai.embeddings.create({ model: "openai/text-embedding-3-small", input: chunks });

        const docs = [];
        for (let i = 0; i < chunks.length; i++) {
          console.log(`📤 Uploading chunk ${i+1}/${chunks.length} for chatbot ${chatbot_id}`);
          // Use database function to properly cast embedding to vector type
          const { data, error } = await insforge.database.rpc("insert_document_with_embedding", {
            p_chatbot_id: chatbot_id,
            p_user_id: body.user_id || "anonymous",
            p_filename: filename,
            p_content: chunks[i],
            p_embedding: emb.data[i].embedding,  // Pass as JSON array
            p_chunk_index: i,
            p_metadata: { total_chunks: chunks.length, source: "django-upload" },
          });
          console.log(`📤 RPC result:`, { data, error });
          if (error) throw error;
          if (data && data.length > 0) {
            docs.push(...data);
          }
        }

        return new Response(JSON.stringify({ success: true, chunks_created: chunks.length, documents: docs }), { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } });
      }

      case "retrieve": {
        if (!query) return new Response(JSON.stringify({ error: "query required" }), { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } });

        const emb = await openai.embeddings.create({ model: "openai/text-embedding-3-small", input: query });
        const qEmb = emb.data[0].embedding;

        const { data, error } = await insforge.database.rpc("match_documents", {
          query_embedding: qEmb,
          match_chatbot_id: chatbot_id,
          match_count: top_k,
          match_threshold: 0.25,
        });
        
        if (error) throw error;
        return new Response(JSON.stringify({ success: true, documents: data || [], count: (data || []).length }), { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } });
      }

      case "retrieve_memory": {
        // Retrieve the bot's own memory (instructions/soul) from vector DB.
        // This is the AGENTS.md equivalent — always present in context.
        const { data: memData, error: memError } = await insforge.database
          .from("documents")
          .select("content, chunk_index, filename")
          .eq("chatbot_id", chatbot_id)
          .like("filename", "memory_%")
          .order("chunk_index", { ascending: true });
        if (memError) throw memError;
        return new Response(JSON.stringify({ success: true, documents: memData || [], count: (memData || []).length }), { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } });
      }

      case "delete": {
        const { error } = await insforge.database.from("documents").delete().eq("chatbot_id", chatbot_id);
        if (error) throw error;
        return new Response(JSON.stringify({ success: true, message: "Documents deleted" }), { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } });
      }

      case "debug_match": {
        // Test match_documents function directly
        const emb = await openai.embeddings.create({ model: "openai/text-embedding-3-small", input: body.query || "horarios" });
        const qEmb = emb.data[0].embedding;

        console.log(`🔍 Debug match: chatbot_id=${chatbot_id}, query="${body.query}"`);
        console.log(`🔍 Query embedding:`, qEmb.slice(0, 5));

        const { data, error } = await insforge.database.rpc("match_documents", {
          query_embedding: qEmb,
          match_chatbot_id: chatbot_id,
          match_count: 10,
          match_threshold: 0.25,
        });
        console.log(`🔍 match_documents result:`, { data, error });
        
        if (error) throw error;
        return new Response(JSON.stringify({ success: true, documents: data || [], count: (data || []).length }), { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } });
      }

      case "ask": {
        // 🔒 VALIDACIÓN DE SEGURIDAD - Solo lectura, query limitado
        if (!query || query.length > 2000) {
          return new Response(JSON.stringify({ error: "Query inválido o demasiado largo (máx 2000 chars)" }), {
            status: 400,
            headers: { ...corsHeaders, "Content-Type": "application/json" },
          });
        }

        // 1. 📤 Recuperar memoria del bot (instructions/soul) desde InsForge
        const { data: memData, error: memError } = await insforge.database
          .from("documents")
          .select("content, chunk_index, filename")
          .eq("chatbot_id", chatbot_id)
          .like("filename", "memory_%")
          .order("chunk_index", { ascending: true });

        let systemPrompt = "";
        if (!memError && memData && memData.length > 0) {
          // Concatenar todos los chunks de memoria ordenados
          const sorted = memData.sort((a: any, b: any) => (a.chunk_index || 0) - (b.chunk_index || 0));
          systemPrompt = sorted.map((d: any) => d.content || "").join("\n");
        }

        // 2. 🔍 Búsqueda semántica con match_documents (RAG)
        const emb = await openai.embeddings.create({
          model: "openai/text-embedding-3-small",
          input: query,
        });
        const qEmb = emb.data[0].embedding;

        const { data: docs, error } = await insforge.database.rpc("match_documents", {
          query_embedding: qEmb,
          match_chatbot_id: chatbot_id,
          match_count: top_k,
          match_threshold: 0.25,  // Lowered from 0.5 to capture more relevant docs
        });

        if (error) throw error;

        // 3. 📋 Construir contexto enriquecido con chunks relevantes
        const relevantChunks = (docs || []).filter(
          (d: any) => d.similarity && d.similarity >= 0.25
        );

        // Contexto concatenado de los chunks más relevantes
        const contextText = relevantChunks
          .sort((a: any, b: any) => (b.similarity || 0) - (a.similarity || 0))
          .map((d: any) => d.content)
          .join("\n\n");

        // 4. 🎯 PROMPT DEL SISTEMA - Diseñado para PREVENIR ALUCINACIONES
        // temperature: 0 se configura en el lado del LLM (OpenRouter/Django)
        const finalPrompt = `
[SISTEMA - INSTRUCCIONES OBLIGATORIAS]
Eres un asistente de IA con identidad y capacidades específicas definidas abajo.
REGLAS ESTRICTAS - NO VIOLAR BAJO NINGUNA CIRCUNSTANCIA:
1. Responde ÚNICAMENTE basándote en el CONTEXTO DOCUMENTAL proporcionado.
2. Si la información NO está en el contexto, responde EXACTAMENTE: "No tengo información sobre eso en mis documentos."
3. NUNCA inventes datos, fechas, nombres, capacidades o características no presentes en el contexto.
4. Mantén la personalidad y tono definidos en las INSTRUCCIONES DEL CHATBOT.
5. Si el usuario pregunta fuera de tus capacidades documentadas, di: "No tengo capacidades para eso según mi configuración."

[INSTRUCCIONES DEL CHATBOT - IDENTIDAD Y CONFIGURACIÓN]
${systemPrompt || "[No hay configuración de chatbot disponible]"}

[CONTEXTO DOCUMENTAL RELEVANTE - FRAGMENTOS RECUPERADOS]
${contextText || "[No hay documentos relevantes para esta pregunta]"}

[PREGUNTA DEL USUARIO]
${query}

[RESPUESTA - Basada exclusivamente en el contexto anterior]:
`.trim();

        return new Response(JSON.stringify({ 
          answer: finalPrompt, // Este prompt se envía al LLM con temperature: 0
          context_chunks: relevantChunks,
          system_prompt: systemPrompt,
          token_count: finalPrompt.length
        }), { 
          status: 200, 
          headers: { ...corsHeaders, "Content-Type": "application/json" } 
        });
      }

      default:
        return new Response(JSON.stringify({ error: "Invalid action" }), { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } });
    }
  } catch (e: any) {
    console.error("❌ Error en handler:", e.message);
    return new Response(JSON.stringify({ error: e.message || "Internal error" }), { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } });
  }
}