"""
ARKA Form Filling Pipeline

A sophisticated pipeline for filling complex web forms using a hybrid model approach:
- gpt-5.2: Vision tasks (extract questions, fill fields)  
- o1: Deep reasoning (when confused, final review)

Architecture:
1. Extract one question at a time (gpt-5.2 vision)
2. Search memory for answer
3. If confused → escalate to o1 for reasoning
4. Fill the field (gpt-5.2 vision)
5. Repeat for all fields
6. Final review by o1 before submission
"""

import time
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from arka.config import get_config
from arka.core.model_router import ModelRouter
from arka.core.browser_manager import get_browser_manager
from arka.memory.memory_client import MemoryClient


@dataclass
class FormField:
    """Represents a single form field."""
    element_id: str
    question: str
    field_type: str  # "input", "select", "textarea"
    answer: Optional[str] = None
    source: str = ""  # "memory", "reasoning", "user"
    confidence: float = 0.0


@dataclass
class FormReviewResult:
    """Result of o1's form review."""
    approved: bool
    changes: List[Dict] = field(default_factory=list)
    reasoning: str = ""


class FormFillingPipeline:
    """
    Orchestrates form filling with hybrid model approach.
    
    Flow:
    1. Extract all form fields (gpt-5.2 vision)
    2. For each field:
       a. Search memory for answer
       b. If not found/confused → escalate to o1
       c. Fill the field
    3. Extract filled form summary (gpt-5.2 vision)
    4. Send to o1 for final review
    5. Apply corrections if needed
    6. Submit
    """
    
    def __init__(self, router: ModelRouter, memory: MemoryClient):
        self.router = router
        self.memory = memory
        self.browser = get_browser_manager()
        self.config = get_config()
        
        # Model assignments
        self.vision_model = self.config.models.gui_vision      # gpt-5.2
        self.reasoner_model = self.config.models.gui_reasoner  # o1
        
        # State
        self.fields: List[FormField] = []
        self.user_node = "tohin_the_user"  # Default user memory node
        
    def fill_form(self, task_context: str = "") -> Dict:
        """
        Main entry point for form filling.
        
        Returns:
            Dict with status, filled_fields, and any errors
        """
        result = {
            "status": "pending",
            "filled_fields": [],
            "errors": [],
            "review_result": None
        }
        
        try:
            # Phase 1: Extract all form fields
            print("📋 Phase 1: Extracting form fields...")
            self.fields = self._extract_form_fields()
            print(f"   Found {len(self.fields)} fields")
            
            if not self.fields:
                result["status"] = "error"
                result["errors"].append("No form fields found")
                return result
            
            # Phase 2: Fill each field
            print("\n✏️ Phase 2: Filling fields one by one...")
            for i, field in enumerate(self.fields):
                print(f"\n   [{i+1}/{len(self.fields)}] {field.question[:50]}...")
                
                # Step 2a: Find answer
                answer, source, confidence = self._find_answer(field.question)
                field.answer = answer
                field.source = source
                field.confidence = confidence
                
                if answer:
                    print(f"   → Answer: '{answer}' (source: {source}, confidence: {confidence:.2f})")
                    
                    # Step 2b: Fill the field
                    success = self._fill_field(field)
                    if success:
                        result["filled_fields"].append({
                            "question": field.question,
                            "answer": answer,
                            "source": source
                        })
                    else:
                        result["errors"].append(f"Failed to fill: {field.question}")
                else:
                    print(f"   → Could not find answer, skipping...")
                    result["errors"].append(f"No answer for: {field.question}")
                
                # Small delay between fields
                time.sleep(1)
            
            # Phase 3: Final review
            print("\n🔍 Phase 3: Final review by reasoning model...")
            review = self._final_review(task_context)
            result["review_result"] = review
            
            if review.approved:
                print("   ✅ Review approved!")
                result["status"] = "ready_to_submit"
            else:
                print(f"   ⚠️ Review requested changes: {len(review.changes)}")
                # Apply corrections
                for change in review.changes:
                    self._apply_correction(change)
                result["status"] = "corrected"
            
            return result
            
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))
            return result
    
    def _extract_form_fields(self) -> List[FormField]:
        """
        Extract all form fields from current page using gpt-5.2 vision.
        """
        # Get DOM snapshot for field IDs
        dom = self.browser.get_dom_snapshot()
        
        # Get screenshot for visual context
        screenshot_b64 = self._capture_screenshot()
        
        prompt = """Analyze this form and extract ALL input fields.

DOM Elements:
{dom}

For each field, identify:
1. The element ID (from DOM, e.g., "4")
2. The question/label text
3. The field type (input, select, textarea)

Return JSON array:
[
  {{"id": "1", "question": "What is your expected salary?", "type": "input"}},
  {{"id": "4", "question": "Do you have a valid passport?", "type": "select"}},
  ...
]

IMPORTANT: Include ALL visible form fields. Only return the JSON array, no other text.""".format(dom=dom[:3000])
        
        response = self.router.chat(
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{screenshot_b64}", "detail": "high"}}
                ]
            }],
            model=self.vision_model,
            max_tokens=1500
        )
        
        # Parse response
        content = response.get("content", "")
        try:
            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            fields_data = json.loads(content)
            return [
                FormField(
                    element_id=f["id"],
                    question=f["question"],
                    field_type=f.get("type", "input")
                )
                for f in fields_data
            ]
        except Exception as e:
            print(f"   Error parsing fields: {e}")
            return []
    
    def _find_answer(self, question: str) -> Tuple[Optional[str], str, float]:
        """
        Find answer for a question.
        
        Returns:
            (answer, source, confidence)
        """
        # Step 1: Search memory
        answer, confidence = self._search_memory(question)
        
        if answer and confidence > 0.7:
            return answer, "memory", confidence
        
        # Step 2: Escalate to o1 for reasoning
        print(f"   🧠 Escalating to reasoning model...")
        answer = self._reason_answer(question, answer, confidence)
        
        if answer:
            return answer, "reasoning", 0.9
        
        return None, "", 0.0
    
    def _search_memory(self, question: str) -> Tuple[Optional[str], float]:
        """
        Search memory for answer to question.
        """
        try:
            results = self.memory.search(
                question,
                limit=5,
                filter_metadata={"node": self.user_node}
            )
            
            if not results:
                return None, 0.0
            
            # Use gpt-5.2 to extract answer from memory results
            memory_context = "\n".join([r.content[:200] for r in results])
            
            prompt = f"""Question: {question}

Memory context:
{memory_context}

Extract the answer from the memory context. If the answer is clearly stated, return it.
If the answer is not in the context, return "NOT_FOUND".

Answer (be concise, just the value):"""

            response = self.router.chat(
                messages=[{"role": "user", "content": prompt}],
                model=self.vision_model,
                max_tokens=100
            )
            
            answer = response.get("content", "").strip()
            
            if answer and "NOT_FOUND" not in answer.upper():
                return answer, 0.8
            
            return None, 0.0
            
        except Exception as e:
            print(f"   Memory search error: {e}")
            return None, 0.0
    
    def _reason_answer(self, question: str, partial_answer: Optional[str], confidence: float) -> Optional[str]:
        """
        Use o1 to reason about the answer when memory search fails or is uncertain.
        """
        # Get full user context from memory
        user_context = ""
        try:
            results = self.memory.search("user profile information", limit=10, filter_metadata={"node": self.user_node})
            user_context = "\n".join([r.content[:300] for r in results])
        except:
            pass
        
        prompt = f"""I'm filling out a job application form and need to answer this question:

QUESTION: {question}

USER PROFILE (from memory):
{user_context if user_context else "No user profile available."}

{f"PARTIAL ANSWER (low confidence {confidence:.0%}): {partial_answer}" if partial_answer else ""}

Based on the user profile, what should the answer be?
Consider:
- Common form question patterns
- Reasonable defaults for a student/job seeker
- What makes sense given the context

If you can determine an answer, provide it.
If the question requires information not available, say "NEED_USER_INPUT".

ANSWER (be concise, just the value):"""

        try:
            response = self.router.chat(
                messages=[{"role": "user", "content": prompt}],
                model=self.reasoner_model,
                max_tokens=200
            )
            
            answer = response.get("content", "").strip()
            
            if answer and "NEED_USER_INPUT" not in answer.upper():
                return answer
            
        except Exception as e:
            print(f"   Reasoning error: {e}")
        
        return None
    
    def _fill_field(self, field: FormField) -> bool:
        """
        Fill a single form field.
        """
        try:
            if field.field_type == "select":
                result = self.browser.select_option(field.element_id, field.answer)
                return "Selected" in str(result)
            else:
                self.browser.type_text(field.element_id, field.answer)
                return True
        except Exception as e:
            print(f"   Fill error: {e}")
            return False
    
    def _final_review(self, task_context: str) -> FormReviewResult:
        """
        Have o1 review the entire filled form before submission.
        """
        # Build summary of filled form
        form_summary = "FILLED FORM SUMMARY:\n"
        for field in self.fields:
            status = f"'{field.answer}'" if field.answer else "[EMPTY]"
            form_summary += f"- {field.question[:60]} → {status} (source: {field.source})\n"
        
        # Get user context
        user_context = ""
        try:
            results = self.memory.search("user profile", limit=5, filter_metadata={"node": self.user_node})
            user_context = "\n".join([r.content[:200] for r in results])
        except:
            pass
        
        prompt = f"""Review this filled job application form before submission.

{form_summary}

USER PROFILE:
{user_context if user_context else "No profile available."}

TASK CONTEXT: {task_context}

REVIEW CHECKLIST:
1. Are all answers consistent with the user profile?
2. Are any answers obviously wrong or contradictory?
3. Are there any empty required fields that should be filled?

RESPOND with JSON:
{{"approved": true}} 
OR
{{"approved": false, "changes": [{{"field": "question text", "current": "current answer", "should_be": "correct answer", "reason": "why"}}]}}"""

        try:
            response = self.router.chat(
                messages=[{"role": "user", "content": prompt}],
                model=self.reasoner_model,
                max_tokens=500
            )
            
            content = response.get("content", "")
            
            # Parse JSON response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            data = json.loads(content)
            
            return FormReviewResult(
                approved=data.get("approved", True),
                changes=data.get("changes", []),
                reasoning=data.get("reason", "")
            )
            
        except Exception as e:
            print(f"   Review parsing error: {e}")
            # Default to approved if parsing fails
            return FormReviewResult(approved=True)
    
    def _apply_correction(self, change: Dict) -> bool:
        """
        Apply a correction suggested by the review.
        """
        field_question = change.get("field", "")
        new_answer = change.get("should_be", "")
        
        # Find the field
        for field in self.fields:
            if field_question.lower() in field.question.lower():
                print(f"   Correcting: {field.question[:40]}... → {new_answer}")
                field.answer = new_answer
                return self._fill_field(field)
        
        return False
    
    def _capture_screenshot(self) -> str:
        """Capture screenshot and return base64."""
        import subprocess
        import base64
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            temp_path = f.name
        
        try:
            subprocess.run(['screencapture', '-x', temp_path], check=True)
            with open(temp_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


# Convenience function
def get_form_pipeline(router: ModelRouter = None, memory: MemoryClient = None) -> FormFillingPipeline:
    """Get or create form filling pipeline."""
    from arka.core.model_router import ModelRouter
    from arka.memory.memory_client import MemoryClient
    
    if router is None:
        router = ModelRouter()
    if memory is None:
        memory = MemoryClient()
    
    return FormFillingPipeline(router, memory)
