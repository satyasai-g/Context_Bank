import re
import collections
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.database.models import ContextTrigger
from backend.schemas.triggers import normalize_trigger_word

# Standard English stop words
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "arent", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "cant", "cannot", "could", "couldnt", "did", "didnt", "do", "does", "doesnt",
    "doing", "dont", "down", "during", "each", "few", "for", "from", "further", "had", "hadnt",
    "has", "hasnt", "have", "havent", "having", "he", "hed", "hell", "hes", "her", "here",
    "heres", "hers", "herself", "him", "himself", "his", "how", "hows", "i", "id", "ill", "im",
    "ive", "if", "in", "into", "is", "isnt", "it", "its", "itself", "lets", "me", "more", "most",
    "mustnt", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shant", "she",
    "shed", "shell", "shes", "should", "shouldnt", "so", "some", "such", "than", "that", "thats",
    "the", "their", "theirs", "them", "themselves", "then", "there", "theres", "these", "they",
    "theyd", "theyll", "theyre", "theyve", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "wasnt", "we", "wed", "well", "were", "weve", "werent",
    "what", "whats", "when", "whens", "where", "wheres", "which", "while", "who", "whos",
    "whom", "why", "whys", "with", "wont", "would", "wouldnt", "you", "youd", "youll", "youre",
    "youve", "your", "yours", "yourself", "yourselves", "user", "assistant", "system", "please",
    "help", "can", "want", "like", "need", "make", "create", "using", "use", "file", "code",
    "step", "steps", "thanks", "yes", "okay", "sure", "now", "here", "also", "work", "first",
    "voice-first", "second", "third", "good", "great", "sounds", "decided", "design", "agreed"
}


class TriggerGeneratorService:
    """
    Intelligent Trigger Generator:
    Automatically extracts high-quality, memorable trigger words directly from chat content.
    """

    @classmethod
    def generate_triggers_from_chat(
        cls,
        chat_text: str,
        db: Optional[Session] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze chat text and generate:
        - primary_trigger (e.g. VOXCENT)
        - alternative_triggers (aliases)
        - reasoning (explanation of why this trigger word was chosen)
        - candidates (ranked list of alternative names)
        """
        if not chat_text or not chat_text.strip():
            return {
                "primary_trigger": "CONTEXT",
                "alternative_triggers": ["NOTES", "CHAT"],
                "reasoning": "Default fallback (empty input).",
                "candidates": ["CONTEXT", "NOTES", "CHAT"],
            }

        # 1. Try Gemini AI if available
        if settings.gemini_available:
            try:
                ai_res = cls._generate_with_gemini(chat_text)
                if ai_res and ai_res.get("primary_trigger"):
                    return cls._resolve_collisions(ai_res, db, user_id)
            except Exception:
                # Fallback to local heuristic extractor
                pass

        # 2. Local rule-based & NLP heuristic extractor
        heuristic_res = cls._generate_heuristic(chat_text)
        return cls._resolve_collisions(heuristic_res, db, user_id)

    @classmethod
    def _generate_with_gemini(cls, chat_text: str) -> Dict[str, Any]:
        """Use Gemini to analyze chat and produce concise trigger words."""
        import json
        from google import genai
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        prompt = f"""
You are the Trigger Naming Engine for Context Bank.
Analyze this chat/conversation and determine the BEST trigger word to retrieve this context in the future.
A trigger word should be:
- 1 to 2 words max, uppercase (e.g., VOXCENT, SQLPATH, AUTH_JWT, RESUME, DOCKER_SETUP).
- Memorable, concise, and specific to the project, topic, or system discussed.

Return ONLY valid JSON matching this structure:
{{
  "primary_trigger": "UPPERCASE_TRIGGER",
  "alternative_triggers": ["ALIAS_1", "ALIAS_2"],
  "reasoning": "1 sentence explanation of why this trigger word best identifies the conversation."
}}

Chat conversation:
{chat_text[:8000]}
"""
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
        )

        resp_text = response.text or ""
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", resp_text)
        json_str = match.group(1) if match else resp_text

        data = json.loads(json_str)

        # Normalize triggers
        primary = cls._clean_trigger(data.get("primary_trigger", "PROJECT"))
        alts = [cls._clean_trigger(a) for a in data.get("alternative_triggers", []) if a]
        alts = [a for a in alts if a != primary][:3]

        return {
            "primary_trigger": primary,
            "alternative_triggers": alts,
            "reasoning": data.get("reasoning", "Generated by AI based on conversation subject."),
            "candidates": [primary] + alts,
        }

    @classmethod
    def _generate_heuristic(cls, chat_text: str) -> Dict[str, Any]:
        """
        Extract trigger words using NLP heuristics, pattern matching, and term frequency.
        """
        candidates: List[Tuple[str, int, str]] = []  # (trigger, score, reason)

        # Pattern A: Explicit Project / System Declarations
        name_patterns = [
            (r"(?:called|named|titled|dubbed)\s+['\"`]?([A-Za-z0-9_-]{3,25})['\"`]?", 120, "Explicit project declaration"),
            (r"(?:project|app|application|system|repo|tool|assistant|package|library|module|service|bot)\s+(?:named|called|is|named:?|called:?)\s+['\"`]?([A-Za-z0-9_-]{3,20})['\"`]?", 110, "Explicit project declaration"),
            (r"(?:building|developing|designing|creating)\s+(?:a|an)\s+(?:new\s+)?([A-Za-z0-9_-]{3,20})\s+(?:project|app|system|application|tool|bot)", 90, "Explicit project action"),
            (r"#+\s*([A-Za-z0-9_-]{3,25})", 60, "Document / Conversation Header"),
        ]

        for pat, score, reason in name_patterns:
            matches = re.findall(pat, chat_text, re.IGNORECASE)
            for m in matches:
                clean = cls._clean_trigger(m)
                if clean and clean.lower() not in STOP_WORDS and len(clean) >= 3:
                    candidates.append((clean, score, reason))

        # Pattern B: CamelCase or PascalCase terms (e.g. VoxCent -> VOXCENT, StripeCheckout -> STRIPE_CHECKOUT)
        camel_matches = re.findall(r"\b([A-Z][a-z0-9]+[A-Z][a-zA-Z0-9]*)\b", chat_text)
        for cm in camel_matches:
            s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", cm)
            snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).upper()
            clean = cls._clean_trigger(snake)
            if clean and len(clean) >= 3 and clean.lower() not in STOP_WORDS:
                candidates.append((clean, 75, f"Code/system entity: {cm}"))
            # Also add exact uppercase without underscores (e.g. POSTGRESQL)
            raw_upper = cls._clean_trigger(cm)
            if raw_upper and raw_upper != clean:
                candidates.append((raw_upper, 70, f"Code entity: {cm}"))

        # Pattern C: ALL_CAPS technical terms or triggers (e.g. FASTAPI, JWT, DOCKER, SQL, REDIS)
        caps_matches = re.findall(r"\b([A-Z0-9_]{3,15})\b", chat_text)
        for cap in caps_matches:
            if cap.lower() not in STOP_WORDS and not cap.isdigit():
                candidates.append((cap, 30, "Technical acronym/keyword"))

        # Pattern D: High-frequency distinct domain nouns
        words = re.findall(r"\b[a-zA-Z]{3,15}\b", chat_text.lower())
        meaningful_words = [w for w in words if w not in STOP_WORDS]
        counts = collections.Counter(meaningful_words)

        top_words = counts.most_common(5)
        if len(top_words) >= 2:
            # Create a 2-word composite trigger (e.g. SQL_INDEX or VOICE_ASSISTANT)
            composite = f"{top_words[0][0]}_{top_words[1][0]}".upper()
            clean_comp = cls._clean_trigger(composite)
            if clean_comp:
                candidates.append((clean_comp, 40, f"Dominant conversation themes: {top_words[0][0]} & {top_words[1][0]}"))

        for word, count in top_words:
            clean_w = cls._clean_trigger(word)
            if clean_w and len(clean_w) >= 3:
                candidates.append((clean_w, 20 + count, f"Frequently mentioned topic: '{word}'"))

        # Sort candidates by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)

        if not candidates:
            return {
                "primary_trigger": "CONTEXT",
                "alternative_triggers": ["PROJECT", "NOTES"],
                "reasoning": "Generic fallback based on chat notes.",
                "candidates": ["CONTEXT", "PROJECT", "NOTES"],
            }

        # Deduplicate candidates preserving order
        unique_triggers: List[Tuple[str, str]] = []
        seen = set()
        for trig, score, reason in candidates:
            if trig not in seen:
                seen.add(trig)
                unique_triggers.append((trig, reason))

        primary = unique_triggers[0][0]
        primary_reason = unique_triggers[0][1]
        alternatives = [t[0] for t in unique_triggers[1:4]]

        return {
            "primary_trigger": primary,
            "alternative_triggers": alternatives,
            "reasoning": f"Derived from {primary_reason.lower()}.",
            "candidates": [t[0] for t in unique_triggers[:5]],
        }

    @classmethod
    def _clean_trigger(cls, raw: str) -> str:
        """Sanitize word into a standard uppercase trigger."""
        if not raw:
            return ""
        # Remove non-alphanumeric except underscore and hyphen
        cleaned = re.sub(r"[^A-Za-z0-9_-]", "", raw).strip()
        cleaned = cleaned.upper()
        # Truncate if too long
        if len(cleaned) > 25:
            cleaned = cleaned[:25].rstrip("_-")
        return cleaned

    @classmethod
    def _resolve_collisions(
        cls,
        result: Dict[str, Any],
        db: Optional[Session],
        user_id: Optional[str],
    ) -> Dict[str, Any]:
        """
        If database and user_id are provided, check if primary_trigger already exists in user's namespace.
        If it does, append an increment or pick the best alternative to prevent conflict.
        """
        if not db or not user_id:
            return result

        primary = result["primary_trigger"]

        # Check if already taken by this user
        existing = db.query(ContextTrigger).filter(
            ContextTrigger.user_id == user_id,
            ContextTrigger.trigger_word == primary,
        ).first()

        if existing:
            # Try first alternative
            alts = result.get("alternative_triggers", [])
            found_alt = None
            for alt in alts:
                alt_collision = db.query(ContextTrigger).filter(
                    ContextTrigger.user_id == user_id,
                    ContextTrigger.trigger_word == alt,
                ).first()
                if not alt_collision:
                    found_alt = alt
                    break

            if found_alt:
                result["alternative_triggers"].insert(0, primary)
                result["primary_trigger"] = found_alt
                result["reasoning"] += f" (Note: '{primary}' already exists in your bank, so '{found_alt}' was selected)."
            else:
                # Append version number
                for i in range(2, 20):
                    candidate_name = f"{primary}_{i}"
                    c_exists = db.query(ContextTrigger).filter(
                        ContextTrigger.user_id == user_id,
                        ContextTrigger.trigger_word == candidate_name,
                    ).first()
                    if not c_exists:
                        result["primary_trigger"] = candidate_name
                        result["reasoning"] += f" (Note: '{primary}' was already in use; assigned '{candidate_name}')."
                        break

        return result
