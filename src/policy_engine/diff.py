import difflib
from typing import List, Dict, Any, Tuple

class PolicyDiffEngine:
    """
    Computes precise text differences between policy clauses.
    """
    
    def generate_diff(self, text_old: str, text_new: str) -> Dict[str, Any]:
        """
        Generate a structured diff report.
        """
        # Tokenize by words to make it readable (char diff is too noisy, line diff too coarse)
        tokens_old = text_old.split()
        tokens_new = text_new.split()
        
        matcher = difflib.SequenceMatcher(None, tokens_old, tokens_new)
        
        diff_structure = []
        summary = {"added": 0, "removed": 0, "unchanged": 0}
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            chunk_old = " ".join(tokens_old[i1:i2])
            chunk_new = " ".join(tokens_new[j1:j2])
            
            if tag == 'equal':
                diff_structure.append({"type": "unchanged", "text": chunk_old})
                summary["unchanged"] += (i2 - i1)
            elif tag == 'replace':
                diff_structure.append({"type": "modification", "old": chunk_old, "new": chunk_new})
                summary["removed"] += (i2 - i1)
                summary["added"] += (j2 - j1)
            elif tag == 'delete':
                diff_structure.append({"type": "deletion", "text": chunk_old})
                summary["removed"] += (i2 - i1)
            elif tag == 'insert':
                diff_structure.append({"type": "insertion", "text": chunk_new})
                summary["added"] += (j2 - j1)
                
        return {
            "diff_blocks": diff_structure,
            "metrics": summary,
            "human_summary": self._generate_human_summary(summary, diff_structure)
        }

    def _generate_human_summary(self, summary: Dict, blocks: List) -> str:
        """
        Heuristic to generate a one-line summary of the change.
        """
        if summary["added"] > 0 and summary["removed"] == 0:
            return "New requirements or benefits added."
        if summary["removed"] > 0 and summary["added"] == 0:
            return "Some provisions were removed."
        if summary["removed"] > 0 and summary["added"] > 0:
            # Detect numeric changes
            for block in blocks:
                if block["type"] == "modification":
                    # Check for number change
                    import re
                    old_nums = re.findall(r'\d+', block['old'])
                    new_nums = re.findall(r'\d+', block['new'])
                    if old_nums and new_nums:
                        try:
                            v_old = float(old_nums[0])
                            v_new = float(new_nums[0])
                            if v_new > v_old:
                                return f"Value increased from {v_old} to {v_new}"
                            if v_new < v_old:
                                return f"Value decreased from {v_old} to {v_new}"
                        except:
                            pass
            return "Existing clauses modified."
            
        return "No significant textual changes."
