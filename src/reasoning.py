"""
Simplified reasoning module for ChromaDB-based PolicyPulse.

Provides semantic search and answer synthesis without requiring Qdrant.
"""

from typing import List, Dict, Any, Optional
import re
import logging
from .policy_urls import get_application_url
from .drift import compute_drift_timeline, find_max_drift
from .policy_engine.instance import get_engine_components

logger = logging.getLogger(__name__)

# Initialize Policy Engine
try:
    policy_graph, policy_executor, policy_diff = get_engine_components()
    logger.info("Policy Engine initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Policy Engine: {e}")
    policy_graph, policy_executor, policy_diff = None, None, None

# TODO: consider caching frequent queries - seeing ~40% repeat rate in logs
# UPDATE 2024-01: tried redis, too heavy for this use case


def generate_reasoning_trace(
    query: str,
    retrieved_results: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate reasoning trace from ChromaDB query results.
    
    Args:
        query: User's question
        retrieved_results: Results from chromadb_setup.query_documents()
        context: Optional context from query processing (demographics, etc.)
    
    Returns:
        Dict with reasoning steps and synthesized answer
    """
    trace = {
        "query": query,
        "steps": [],
        "retrieved_points": [],
        "final_answer": "",
        "confidence_score": 0.0,
        # debug fields - remove before prod? kept for now
        "_debug_timestamp": None
    }
    
    try:
        # Step 1: Parse retrieved results
        ids = retrieved_results.get('ids', [[]])[0]
        documents = retrieved_results.get('documents', [[]])[0]
        metadatas = retrieved_results.get('metadatas', [[]])[0]
        distances = retrieved_results.get('distances', [[]])[0]
        
        trace["steps"].append({
            "step": 1,
            "action": f"Retrieved {len(documents)} documents from ChromaDB"
        })
        
        # Step 2: Format results for display
        retrieved_points = []
        for i, (doc_id, doc, meta, dist) in enumerate(zip(ids, documents, metadatas, distances)):
            retrieved_points.append({
                "rank": i + 1,
                "id": doc_id,
                "content_preview": doc[:500] if doc else "",
                "policy_id": meta.get("policy_id", "UNKNOWN"),
                "modality": meta.get("modality", "text"),
                "year": meta.get("year", ""),
                "distance": round(dist, 4),
                "score": round(1 - dist, 4),  # Convert distance to similarity
                # Budget metadata
                "allocation_crores": meta.get("allocation_crores", 0),
                "expenditure_crores": meta.get("expenditure_crores", 0)
            })
        
        trace["retrieved_points"] = retrieved_points
        
        trace["steps"].append({
            "step": 2,
            "action": "Formatted retrieved documents"
        })
        
        #Step 3: Synthesize answer
        # NOTE: this was originally calling an LLM but we stripped it out
        # retrieval-only is more deterministic anyway
        answer = synthesize_answer(query, retrieved_points, context)
        trace["final_answer"] = answer
        
        # Step 4: Calculate confidence
        confidence = calculate_confidence(retrieved_points)
        trace["confidence_score"] = confidence
        
        trace["steps"].append({
            "step": 3,
            "action": "Answer synthesized",
            "confidence": confidence
        })
        
        # Step 5: Check for temporal/evolution queries and include drift data
        query_lower = query.lower()
        is_change_query = any(kw in query_lower for kw in [
            "change", "changed", "evolve", "evolved", "evolution", 
            "different", "difference", "compare", "drift", "over time",
            "how has", "what happened", "history", "timeline"
        ])
        
        if is_change_query:
            # Determine policy from retrieved results
            primary_policy = None
            if retrieved_points:
                policy_counts = {}
                for point in retrieved_points[:3]:
                    pid = point.get("policy_id", "UNKNOWN")
                    policy_counts[pid] = policy_counts.get(pid, 0) + 1
                primary_policy = max(policy_counts, key=policy_counts.get) if policy_counts else None
            
            # Also check context for explicit policy
            if context and context.get("policy_id"):
                primary_policy = context.get("policy_id")
                
            if primary_policy and primary_policy != "UNKNOWN":
                try:
                    drift_timeline = compute_drift_timeline(primary_policy)
                    max_drift = find_max_drift(primary_policy)
                    
                    if drift_timeline:
                        trace["drift_timeline"] = drift_timeline
                        trace["drift_max"] = max_drift
                        trace["drift_policy"] = primary_policy
                        trace["steps"].append({
                            "step": 4,
                            "action": f"Computed drift timeline for {primary_policy} ({len(drift_timeline)} year transitions)"
                        })
                        logger.info(f"Drift data added for {primary_policy}: {len(drift_timeline)} transitions")
                except Exception as e:
                    logger.warning(f"Failed to compute drift for {primary_policy}: {e}")
        
    except Exception as e:
        logger.error(f"Reasoning trace generation failed: {e}")
        trace["final_answer"] = f"Error processing query: {str(e)}"
        trace["confidence_score"] = 0.0
    
    return trace


def synthesize_answer(
    query: str,
    retrieved_points: List[Dict[str, Any]],
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Synthesize answer from retrieved documents.
    
    Args:
        query: User's question
        retrieved_points: List of retrieved document dicts
        context: Optional context from query processor
    
    Returns:
        Synthesized answer string
    """
    
    # Check if we are satisfying a previous request for occupation
    chat_history = context.get('chat_history', []) if context else []
    demographics = context.get('demographics', {}) if context else {}
    
    # Look at the last message from the model
    last_bot_msg = None
    for msg in reversed(chat_history):
        if msg.get('role') == 'model':
            last_bot_msg = msg
            break
            
    is_answering_prompt = False
    if last_bot_msg:
        # Check if the last thing bot said was asking for occupation
        if "specify your occupation" in last_bot_msg.get('content', '') or "need to know your occupation" in last_bot_msg.get('content', ''):
            is_answering_prompt = True

    # Detect query type for routing
    query_lower = query.lower()
    is_suggestion = any(w in query_lower for w in ["suggest", "recommend", "which scheme", "what scheme", "policies for", "eligible for"])
    is_what_is = any(w in query_lower for w in ["what is", "what's", "explain", "tell me about", "describe"])
    is_budget = any(w in query_lower for w in ["budget", "allocation", "expenditure", "spending", "crore", "spent"])
    is_eligibility = any(w in query_lower for w in ["eligible", "eligibility", "qualify", "can i get", "am i"])
    is_how_to = any(w in query_lower for w in ["how to", "apply", "application", "register", "enrollment"])

    # Trigger eligibility check if:
    # 1. Explicitly asked ("suggest", "policies for")
    # 2. Answering a prompt
    # 3. Query contains rich demographics (implying "for me") -> UNLESS it's a direct "What is" question
    has_rich_demographics = len(demographics) >= 2 or 'occupation' in demographics
    
    skip_eligibility = (is_what_is or is_budget) and not is_suggestion
    
    if (is_suggestion or is_answering_prompt or (has_rich_demographics and not skip_eligibility)) and demographics:
        from .eligibility import check_eligibility  # Lazy import to avoid circular dep issues
        
        # Check if occupation is missing (skip check for minors)
        is_minor = demographics.get('age', 18) < 18
        if 'occupation' not in demographics and not is_minor:
            return (
                "To provide the best policy suggestions, I need to know your occupation. "
                "Are you a **Student**, **Farmer**, **Entrepreneur**, or **Worker**?\n\n"
                "Please enable me to suggest the most relevant schemes by specifying your occupation."
            )
            
        # Default occupation for minors if missing
        if is_minor and 'occupation' not in demographics:
            demographics['occupation'] = 'student'
            
        # Run eligibility check (returns dict with 'eligible' and 'excluded')
        eligibility_result = check_eligibility(demographics)
        eligible_schemes = eligibility_result.get('eligible', [])
        excluded_schemes = eligibility_result.get('excluded', [])
        
        if eligible_schemes:
            age_str = f"{demographics.get('age')}yr old" if demographics.get('age') else "age unknown"
            occ_str = demographics.get('occupation') if demographics.get('occupation') else "profile"
            sections = [f"Based on your profile ({age_str}, {occ_str}), here are the best policies for you:"]
            
            for scheme in eligible_schemes[:7]:  # Top 7
                sections.append(
                    f"### **{scheme['name']}**\n"
                    f"{scheme['description']}\n"
                    f"**Benefits**: {scheme['benefits']}\n"
                    f"**Apply Link**: [{scheme['application_link']}]({scheme['application_link']})"
                )
            
            # Also show exclusion reasons if any (Why Not feature)
            if excluded_schemes:
                excluded_preview = excluded_schemes[:3]  # Top 3 exclusions
                sections.append("\n---\n**Why you may not qualify for some schemes:**")
                for ex in excluded_preview:
                    if ex.get('reasons'):
                        sections.append(f"- **{ex['name']}**: {', '.join(ex['reasons'])}")
            
            return "\n\n".join(sections)
        else:
            return "Based on the provided details, no specific schemes matched perfectly. However, you can explore general schemes like **Digital India** or **RTI** which are open to all."

    if not retrieved_points:
        return "No relevant information found. Please try rephrasing your question."
    
    # Determine the primary policy from top results
    policy_counts = {}
    for point in retrieved_points[:3]:
        pid = point.get("policy_id", "UNKNOWN")
        policy_counts[pid] = policy_counts.get(pid, 0) + 1
    
    primary_policy = max(policy_counts, key=policy_counts.get) if policy_counts else None
    
    # CONTEXT AWARENESS: If no clear policy in current results, check history
    # This handles queries like "what is the budget?" following a conversation about NREGA
    chat_history = context.get('chat_history', []) if context else []
    if not primary_policy or (primary_policy == "UNKNOWN" and chat_history):
        # Look for policy in last assistant message
        for msg in chat_history:
            if not msg.get("is_user", False): # Check bot messages
                 # Simple heuristic: look for known policy IDs in previous text
                content = msg.get("content", "").upper()
                for known_policy in POLICY_DESCRIPTIONS.keys():
                    if known_policy in content:
                        primary_policy = known_policy
                        break
            if primary_policy: break
            
    # Filter to only include results from primary policy
    if primary_policy and primary_policy != "UNKNOWN":
        filtered_points = [p for p in retrieved_points if p.get("policy_id") == primary_policy]
        # If filtering removed everything (because retrieval failed to find new context), 
        # we arguably should return a "I think you're asking about X" message or fallback
        if not filtered_points and retrieved_points:
             # Soft fallback: don't filter if it means losing all data, unless confidence is high
             pass
    else:
        filtered_points = retrieved_points

    # Extract year from query if mentioned (e.g., "2011", "in 2020")
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', query)
    query_year = year_match.group(1) if year_match else None
    
    # --- GOVERNANCE ENGINE INTEGRATION (Phase 2/3) ---
    governance_section = ""
    if policy_graph and policy_executor and primary_policy and primary_policy != "UNKNOWN":
        try:
            # Determine reference date
            from datetime import date
            ref_date = date.today()
            if query_year:
                try:
                    ref_date = date(int(query_year), 12, 31) # End of year generally safe
                except:
                    pass
            
            # Get active clauses
            active_clauses = policy_graph.get_active_clauses(primary_policy, ref_date)
            
            if active_clauses:
                gov_lines = [f"\n🔍 **Governance Verification ({ref_date.year})**:"]
                
                # If we have demographics, run logic
                if demographics and len(demographics) > 0:
                    gov_lines.append("**Eligibility Logic Trace:**")
                    pass_count = 0
                    fail_count = 0
                    
                    for clause in active_clauses:
                        # Only evaluate clauses with meaningful logic
                        if clause.logic:
                            # We might want to filter relevant tags (e.g. "eligibility")
                            if "eligibility" in clause.tags:
                                passed = policy_executor.evaluate(clause.logic, demographics)
                                icon = "✅" if passed else "❌"
                                
                                # Provenance
                                docs = policy_graph.get_provenance_chain(clause.id)
                                doc_title = docs[0].title if docs else "Unknown Authority"
                                doc_type = docs[0].doc_type if docs else "Clause"
                                
                                msg = f"- {icon} **{doc_type}**: {clause.text} (Source: {doc_title})"
                                if not passed:
                                    reasons = policy_executor.explain_failure(clause.logic, demographics)
                                    if reasons:
                                        msg += f"\n  - *Reason*: {'; '.join(reasons)}"
                                
                                gov_lines.append(msg)
                                if passed: pass_count += 1
                                else: fail_count += 1
                    
                    if pass_count > 0 and fail_count == 0:
                        gov_lines.append(f"\n✅ **Result**: You appear eligible based on {pass_count} active legal clauses.")
                    elif fail_count > 0:
                        gov_lines.append(f"\n❌ **Result**: You are currently ineligible due to {fail_count} unmet conditions.")
                
                else:
                    # Just list the active binding rules if no user profile
                    gov_lines.append("**Active Binding Rules (Verified):**")
                    for clause in active_clauses[:3]: # Limit to top 3 to avoid spam
                         docs = policy_graph.get_provenance_chain(clause.id)
                         source = f"{docs[0].doc_type} {docs[0].id}" if docs else "Official Rule"
                         gov_lines.append(f"- {clause.text} *[{source}]*")
                    if len(active_clauses) > 3:
                         gov_lines.append(f"*(and {len(active_clauses)-3} more active clauses)*")

                governance_section = "\n".join(gov_lines)
                
        except Exception as e:
            logger.error(f"Governance engine error: {e}")
            governance_section = f"\n*(Governance check failed: {str(e)})*"
            
    # ----------------------------------------------------
    
    # Policy descriptions for "what is" queries
    POLICY_DESCRIPTIONS = {
        "NREGA": "The Mahatma Gandhi National Rural Employment Guarantee Act (MGNREGA) is a social security scheme that guarantees 100 days of wage employment per year to rural households willing to do unskilled manual work.",
        "RTI": "The Right to Information Act (RTI) is a law that empowers Indian citizens to request information from public authorities, promoting transparency and accountability in government.",
        "PM-KISAN": "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN) is a government scheme providing income support of ₹6,000 per year to farmer families in three equal installments.",
        "AYUSHMAN-BHARAT": "Ayushman Bharat - Pradhan Mantri Jan Arogya Yojana (PM-JAY) is the world's largest health insurance scheme, providing ₹5 lakh coverage per family per year for hospitalization.",
        "SWACHH-BHARAT": "Swachh Bharat Mission is a nationwide cleanliness campaign providing subsidies for toilet construction and promoting sanitation and hygiene.",
        "DIGITAL-INDIA": "Digital India is a flagship programme to transform India into a digitally empowered society with focus on digital infrastructure, governance, and literacy.",
        "SKILL-INDIA": "Skill India Mission aims to train over 40 crore Indians in various skills through vocational training, certification, and placement assistance.",
        "SMART-CITIES": "Smart Cities Mission aims to promote sustainable and inclusive urban development through technology-driven solutions.",
        "NEP": "The National Education Policy (NEP) 2020 is a comprehensive framework for transforming education in India with focus on holistic development and skill building.",
        "MAKE-IN-INDIA": "Make in India is an initiative to encourage companies to manufacture products in India, boosting employment and economic growth."
    }
    
    # Group by modality
    by_modality = {}
    for point in filtered_points:
        modality = point.get("modality", "text")
        if modality not in by_modality:
            by_modality[modality] = []
        by_modality[modality].append(point)
    
    # Build answer sections
    sections = []
    
    # For "what is" queries, start with policy description
    if is_what_is and primary_policy:
        if primary_policy in POLICY_DESCRIPTIONS:
            sections.append(f"**{primary_policy}**: {POLICY_DESCRIPTIONS[primary_policy]}")
        
        # Add key details from retrieved content
        if filtered_points:
            top = filtered_points[0]
            content = top['content_preview'][:300] if top.get('content_preview') else ""
            if content and len(content) > 50:
                sections.append(f"**Key Details**: {content}")
        
        # Add authoritative citation from eligibility metadata
        from .eligibility import get_policy_details
        policy_details = get_policy_details(primary_policy)
        if policy_details and policy_details.get("metadata"):
            meta = policy_details["metadata"]
            citation_parts = []
            if meta.get("notification_number"):
                citation_parts.append(f"**Notification**: {meta['notification_number']}")
            if meta.get("authority"):
                citation_parts.append(f"**Authority**: {meta['authority']}")
            if meta.get("status"):
                citation_parts.append(f"**Status**: {meta['status']}")
            if meta.get("gazette_url"):
                citation_parts.append(f"**Official Source**: [{meta['gazette_url']}]({meta['gazette_url']})")
            
            if citation_parts:
                sections.append("\n📜 **Proof/Citation**:\n" + " | ".join(citation_parts))
    
    # For budget queries, prioritize budget modality with actual amounts
    elif is_budget:
        budget = by_modality.get("budget", [])
        if budget:
            # Filter by year if specified in query
            if query_year:
                budget = [b for b in budget if str(b.get('year', '')) == query_year]
            
            # Deduplicate by year (multiple text variants exist for same year)
            seen_years = set()
            for b in budget:
                year = b.get('year', 'N/A')
                if year in seen_years:
                    continue
                seen_years.add(year)
                
                allocation = b.get('allocation_crores', 0)
                expenditure = b.get('expenditure_crores', 0)
                policy = b.get('policy_id', 'Unknown')
                
                # Build response with actual numbers
                if allocation > 0:
                    utilization = round((expenditure / allocation) * 100, 1) if allocation > 0 else 0
                    sections.append(
                        f"**{policy} Budget ({year})**:\n"
                        f"• Allocated: ₹{allocation:,.2f} crore\n"
                        f"• Spent: ₹{expenditure:,.2f} crore\n"
                        f"• Utilization: {utilization}%"
                    )
                else:
                    # Fallback to content preview
                    content = b['content_preview'][:400] if b.get('content_preview') else ""
                    sections.append(f"**Budget ({year})**: {content}")
        else:
            # Fallback to general content
            for p in filtered_points[:2]:
                sections.append(f"{p['content_preview'][:400]}")
    
    # For eligibility queries
    elif is_eligibility:
        if primary_policy in POLICY_DESCRIPTIONS:
            sections.append(f"**About {primary_policy}**: {POLICY_DESCRIPTIONS[primary_policy]}")
        sections.append("**Eligibility**: Based on your profile, you may be eligible. Use the eligibility checker or upload your Aadhaar for personalized results.")
    
    # For how-to queries
    elif is_how_to:
        if primary_policy:
            sections.append(f"**How to Apply for {primary_policy}**:")
            sections.append(f"1. Visit the official portal: {get_application_url(primary_policy)}")
            sections.append("2. Keep your Aadhaar card and required documents ready")
            sections.append("3. Fill the application form with accurate details")
            sections.append("4. Submit and save your application reference number")
    
    # Default: show relevant content with context
    else:
        # Add temporal/text info
        temporal = by_modality.get("temporal") or by_modality.get("text", [])
        if temporal:
            top = temporal[0]
            content = top['content_preview'][:400] if top.get('content_preview') else ""
            sections.append(f"**{top['policy_id']} ({top.get('year', 'N/A')})**: {content}")
        
        # Add budget info
        budget = by_modality.get("budget", [])
        if budget:
            top = budget[0]
            content = top['content_preview'][:300] if top.get('content_preview') else ""
            sections.append(f"**Budget ({top.get('year', 'N/A')})**: {content}")
        
        # Add news info
        news = by_modality.get("news", [])
        if news:
            top = news[0]
            content = top['content_preview'][:300] if top.get('content_preview') else ""
            sections.append(f"**Latest Updates ({top.get('year', 'N/A')})**: {content}")
    
    # If no specific modalities, use top result
    if not sections and filtered_points:
        top = filtered_points[0]
        sections.append(f"{top['content_preview'][:500]}")
    
    return ("\n\n".join(sections) + "\n" + governance_section) if sections else "No detailed information available."


def calculate_confidence(retrieved_points: List[Dict[str, Any]]) -> float:
    """
    Calculate confidence based on retrieval scores and result consistency.
    
    Args:
        retrieved_points: List of retrieved documents
    
    Returns:
        Confidence score (0-1)
    """
    if not retrieved_points:
        return 0.0
    
    # Base confidence from top 3 scores
    top_scores = [p.get("score", 0) for p in retrieved_points[:3]]
    base_confidence = sum(top_scores) / len(top_scores) if top_scores else 0.0
    
    # Boost confidence if all top results are from the same policy (consistent)
    policies = [p.get("policy_id") for p in retrieved_points[:3]]
    if len(set(policies)) == 1 and policies[0] is not None:
        # All from same policy = boost by 0.15
        base_confidence = min(base_confidence + 0.15, 1.0)
    
    # Boost if we have multiple modalities (comprehensive answer)
    modalities = set(p.get("modality") for p in retrieved_points[:5])
    if len(modalities) >= 2:
        base_confidence = min(base_confidence + 0.1, 1.0)
    
    return round(min(base_confidence, 1.0), 3)
