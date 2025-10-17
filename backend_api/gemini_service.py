from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import List, Dict, Any
import logging
import re
import unicodedata

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for interacting with Google Gemini API"""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        self.api_key = api_key
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=0.0
        )
        # Embeddings model for vector search (prefer new model, fallback to legacy)
        self.embedder = None
        self.embedder_fallback = None
        try:
            # Newer model name typically requires the 'models/' prefix
            self.embedder = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=api_key)
        except Exception as e:
            logger.error(f"Primary embeddings init failed: {e}")
            try:
                # Legacy embedding model
                self.embedder_fallback = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
            except Exception as e2:
                logger.error(f"Fallback embeddings init failed: {e2}")
    
    def chat(
        self, 
        user_message: str, 
        system_prompt: str = None,
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """Send a chat message and get response"""
        messages = []
        
        # Add system prompt
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                if msg['role'] == 'user':
                    messages.append(HumanMessage(content=msg['content']))
                elif msg['role'] == 'assistant':
                    messages.append(AIMessage(content=msg['content']))
        
        # Add current user message
        messages.append(HumanMessage(content=user_message))
        
        try:
            response = self.llm.invoke(messages)
            content = response.content
            
            # Clean up markdown formatting that might interfere with display
            content = self._clean_response_formatting(content)
            
            # Enforce word limit for chat responses too
            content = self._enforce_word_limit(content, max_words=100)

            return content
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a list of texts."""
        if not texts:
            return []
        # Try primary embedder, then fallback if needed
        embedder_chain = [self.embedder, self.embedder_fallback]
        last_error = None
        for emb in embedder_chain:
            if not emb:
                continue
            try:
                return emb.embed_documents(texts)
            except Exception as e:
                last_error = e
                logger.error(f"Error generating embeddings: {e}")
        if last_error:
            logger.error(f"All embedding attempts failed: {last_error}")
        return []
    
    def verify_answer_supported(self, context: str, answer: str) -> bool:
        """Verify that the answer is supported by the provided context.
        Returns True if supported, False if the model flags unsupported claims.
        """
        if not answer:
            return False
        try:
            verifier = ChatGoogleGenerativeAI(
                model=self.llm.model,
                google_api_key=self.api_key,
                temperature=0.0
            )
            prompt = (
                "You are a strict fact-checker. Given CONTEXT and ANSWER, "
                "reply with a single token: OK if every factual claim in ANSWER "
                "is directly supported by CONTEXT, otherwise UNSUPPORTED.\n\n"
                f"CONTEXT:\n{context}\n\nANSWER:\n{answer}"
            )
            result = verifier.invoke([HumanMessage(content=prompt)])
            text = (result.content or "").strip().upper()
            if "UNSUPPORTED" in text:
                return False
            return True
        except Exception as e:
            logger.error(f"Verifier failed: {e}")
            # Fail-safe: if verifier errors, do not block the answer
            return True

    def analyze_telemetry(
        self, 
        question: str, 
        telemetry_data: Dict[str, Any],
        context: str = ""
    ) -> str:
        """Analyze telemetry data and answer question with enhanced intelligence"""
        
        # Create a focused prompt for telemetry analysis
        system_prompt = """You are an expert UAV flight data analyst specializing in ArduPilot/MAVLink telemetry.
Your role is to help users understand their flight data by providing clear, concise analysis.

ANALYSIS GUIDELINES:
- Provide specific, data-driven answers with exact values
- Reference actual statistics and data points from the telemetry
- Highlight any safety concerns, anomalies, or critical issues
- Use clear, non-technical language when possible
- If data is missing, clearly state what information is not available
- Respond in plain text format, do not use markdown code blocks
- Keep responses conversational but informative

RESPONSE REQUIREMENTS:
- MAXIMUM 100 words per response
- Be concise and direct
- Focus on the most important information
- Include specific data values when available
- Mention safety concerns if any
- Avoid unnecessary explanations or repetition
"""
        
        # Format telemetry data for the LLM
        telemetry_summary = self._format_telemetry_for_llm(telemetry_data)
        
        user_prompt = f"""FLIGHT DATA ANALYSIS REQUEST:

{context}

USER QUESTION: {question}

AVAILABLE TELEMETRY DATA:
{telemetry_summary}

Please provide a concise analysis (MAXIMUM 100 words). Include:
1. Direct answer with specific values
2. Key supporting data
3. Any safety concerns

Be specific and reference actual data values when available. Keep it brief and focused."""
        
        response = self.chat(user_prompt, system_prompt)
        
        # Additional cleanup for telemetry analysis responses
        response = self._clean_response_formatting(response)
        
        # Enforce 100-word limit
        response = self._enforce_word_limit(response, max_words=100)
        
        return response
    
    def _format_telemetry_for_llm(self, telemetry_data: Dict[str, Any]) -> str:
        """Format telemetry data in a readable way for the LLM"""
        formatted = []
        
        for param, data in telemetry_data.items():
            if isinstance(data, dict):
                formatted.append(f"\n{param}:")
                
                # Add statistics if available
                if 'statistics' in data and data['statistics']:
                    stats = data['statistics']
                    formatted.append(f"  Statistics:")
                    for key, value in stats.items():
                        if isinstance(value, (int, float)):
                            formatted.append(f"    - {key}: {value:.2f}")
                        else:
                            formatted.append(f"    - {key}: {value}")
                
                # Add data points count
                if 'count' in data:
                    formatted.append(f"  Data points: {data['count']}")
                
                # Add sample data (first few points)
                if 'data' in data and isinstance(data['data'], list):
                    sample_size = min(5, len(data['data']))
                    if sample_size > 0:
                        formatted.append(f"  Sample data (first {sample_size} points):")
                        for i, point in enumerate(data['data'][:sample_size]):
                            formatted.append(f"    {i+1}. {point}")
        
        return '\n'.join(formatted)
    
    def _clean_response_formatting(self, content: str) -> str:
        """Clean up response formatting to remove problematic markdown"""
        if not content:
            return content
        
        # Remove markdown code blocks
        content = content.replace('```text', '').replace('```json', '').replace('```', '')
        
        # Remove excessive newlines
        content = content.replace('\n\n\n', '\n\n')
        
        # Remove leading/trailing whitespace
        content = content.strip()
        
        return content
    
    def _enforce_word_limit(self, content: str, max_words: int = 100) -> str:
        """Enforce word limit on response content"""
        if not content:
            return content
        
        words = content.split()
        if len(words) <= max_words:
            return content
        
        # Truncate to max_words and add ellipsis if needed
        truncated_words = words[:max_words]
        truncated_content = ' '.join(truncated_words)
        
        # Ensure we end with a complete sentence if possible
        if not truncated_content.endswith(('.', '!', '?')):
            # Find the last complete sentence
            sentences = truncated_content.split('. ')
            if len(sentences) > 1:
                truncated_content = '. '.join(sentences[:-1]) + '.'
            else:
                truncated_content += '...'
        
        return truncated_content

    # -------------------- Optional DDG web search (opt-in) --------------------
    def ddg_search(self, query: str, site: str | None = None, k: int = 5) -> list[str]:
        """Lightweight DuckDuckGo search using public HTML results.
        Returns a list of result snippets/links as strings. Kept minimal to avoid extra deps.
        """
        try:
            import requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'
            }
            q = query.strip()
            if site:
                q = f"site:{site} " + q
            params = { 'q': q }
            r = requests.get('https://duckduckgo.com/html/', params=params, headers=headers, timeout=15)
            r.raise_for_status()
            html = r.text
            # crude extraction of links + snippets (avoid full parser to keep dependencies small)
            # pattern targets result blocks
            items = []
            for m in re.finditer(r'<a rel="nofollow" class="result__a" href="(.*?)".*?>(.*?)</a>.*?<a.*?class="result__url".*?>(.*?)</a>', html, re.S):
                url = m.group(1)
                title = re.sub('<.*?>', '', m.group(2))
                disp = re.sub('<.*?>', '', m.group(3))
                items.append(f"{title}\n{url}\n{disp}")
                if len(items) >= k:
                    break
            return items
        except Exception as e:
            logger.error(f"DDG search error: {e}")
            return []

    # -------------------- Output sanitization --------------------
    def sanitize_plain_ascii(self, text: str) -> str:
        """Convert to plain ASCII, remove brackets, asterisks, backticks, and compress whitespace."""
        if not text:
            return text
        # Normalize and strip diacritics
        normalized = unicodedata.normalize('NFKD', text)
        ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
        # Remove special markup characters and square brackets
        cleaned = re.sub(r"[\[\]`*]+", "", ascii_text)
        # Collapse whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def redact_session_ids(self, text: str) -> str:
        """Redact session identifiers like 'session_<alnum>' that may appear in context/answers."""
        if not text:
            return text
        try:
            # Common patterns: session_<id>, SESSION <id>
            text = re.sub(r"session_[a-zA-Z0-9_-]+", "[session]", text, flags=re.IGNORECASE)
            text = re.sub(r"SESSION\s+[a-zA-Z0-9_-]+", "SESSION [id]", text)
        except Exception:
            return text
        return text

