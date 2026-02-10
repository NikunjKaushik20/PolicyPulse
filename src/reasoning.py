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
   
    trace = {
        "query": query,
        "steps": [],
        "retrieved_points": [],
        "final_answer": "",
        "confidence_score": 0.0,
        "_debug_timestamp": None
    }
    
    try:
       
        ids = retrieved_results.get('ids', [[]])[0]
        documents = retrieved_results.get('documents', [[]])[0]
        metadatas = retrieved_results.get('metadatas', [[]])[0]
        distances = retrieved_results.get('distances', [[]])[0]
        
        trace["steps"].append({
            "step": 1,
            "action": f"Retrieved {len(documents)} documents from ChromaDB"
        })
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
                "score": round(1 - dist, 4),  
                "allocation_crores": meta.get("allocation_crores", 0),
                "expenditure_crores": meta.get("expenditure_crores", 0)
            })
        
        trace["retrieved_points"] = retrieved_points
        
        trace["steps"].append({
            "step": 2,
            "action": "Formatted retrieved documents"
        })

        answer = synthesize_answer(query, retrieved_points, context)
        trace["final_answer"] = answer
        
        confidence = calculate_confidence(retrieved_points)
        trace["confidence_score"] = confidence
        
        trace["steps"].append({
            "step": 3,
            "action": "Answer synthesized",
            "confidence": confidence
        })
        
        
        query_lower = query.lower()
        is_change_query = any(kw in query_lower for kw in [
            "change", "changed", "evolve", "evolved", "evolution", 
            "different", "difference", "compare", "drift", "over time",
            "how has", "what happened", "history", "timeline"
        ])
        
        if is_change_query:
            
            primary_policy = None
            if retrieved_points:
                policy_counts = {}
                for point in retrieved_points[:3]:
                    pid = point.get("policy_id", "UNKNOWN")
                    policy_counts[pid] = policy_counts.get(pid, 0) + 1
                primary_policy = max(policy_counts, key=policy_counts.get) if policy_counts else None
            
            
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

    
   
    chat_history = context.get('chat_history', []) if context else []
    demographics = context.get('demographics', {}) if context else {}
    
    
    last_bot_msg = None
    for msg in reversed(chat_history):
        if msg.get('role') == 'model':
            last_bot_msg = msg
            break
            
    is_answering_prompt = False
    if last_bot_msg:
        
        if "specify your occupation" in last_bot_msg.get('content', '') or "need to know your occupation" in last_bot_msg.get('content', ''):
            is_answering_prompt = True

    
    query_lower = query.lower()
    is_suggestion = any(w in query_lower for w in ["suggest", "recommend", "which scheme", "what scheme", "policies for", "eligible for"])
    is_what_is = any(w in query_lower for w in ["what is", "what's", "explain", "tell me about", "describe"])
    is_budget = any(w in query_lower for w in ["budget", "allocation", "expenditure", "spending", "crore", "spent"])
    is_eligibility = any(w in query_lower for w in ["eligible", "eligibility", "qualify", "can i get", "am i"])
    is_how_to = any(w in query_lower for w in ["how to", "apply", "application", "register", "enrollment"])

   
    has_rich_demographics = len(demographics) >= 2 or 'occupation' in demographics
    
    skip_eligibility = (is_what_is or is_budget) and not is_suggestion
    
    if (is_suggestion or is_answering_prompt or (has_rich_demographics and not skip_eligibility)) and demographics:
        from .eligibility import check_eligibility 
        is_minor = demographics.get('age', 18) < 18
        if 'occupation' not in demographics and not is_minor:
            return (
                "To provide the best policy suggestions, I need to know your occupation. "
                "Are you a **Student**, **Farmer**, **Entrepreneur**, or **Worker**?\n\n"
                "Please enable me to suggest the most relevant schemes by specifying your occupation."
            )
            

        if is_minor and 'occupation' not in demographics:
            demographics['occupation'] = 'student'
            
       
        eligibility_result = check_eligibility(demographics)
        eligible_schemes = eligibility_result.get('eligible', [])
        excluded_schemes = eligibility_result.get('excluded', [])
        
        if eligible_schemes:
            age_str = f"{demographics.get('age')}yr old" if demographics.get('age') else "age unknown"
            occ_str = demographics.get('occupation') if demographics.get('occupation') else "profile"
            sections = [f"Based on your profile ({age_str}, {occ_str}), here are the best policies for you:"]
            
            for scheme in eligible_schemes[:7]:  
                sections.append(
                    f"### **{scheme['name']}**\n"
                    f"{scheme['description']}\n"
                    f"**Benefits**: {scheme['benefits']}\n"
                    f"**Apply Link**: [{scheme['application_link']}]({scheme['application_link']})"
                )
            
        
            if excluded_schemes:
                excluded_preview = excluded_schemes[:3]
                sections.append("\n---\n**Why you may not qualify for some schemes:**")
                for ex in excluded_preview:
                    if ex.get('reasons'):
                        sections.append(f"- **{ex['name']}**: {', '.join(ex['reasons'])}")
            
            return "\n\n".join(sections)
        else:
            return "Based on the provided details, no specific schemes matched perfectly. However, you can explore general schemes like **Digital India** or **RTI** which are open to all."

    if not retrieved_points:
        return "No relevant information found. Please try rephrasing your question."
    
    
    policy_counts = {}
    for point in retrieved_points[:3]:
        pid = point.get("policy_id", "UNKNOWN")
        policy_counts[pid] = policy_counts.get(pid, 0) + 1
    
    primary_policy = max(policy_counts, key=policy_counts.get) if policy_counts else None
    
    
    chat_history = context.get('chat_history', []) if context else []
    if not primary_policy or (primary_policy == "UNKNOWN" and chat_history):

        for msg in chat_history:
            if not msg.get("is_user", False):
                content = msg.get("content", "").upper()
                for known_policy in POLICY_DESCRIPTIONS.keys():
                    if known_policy in content:
                        primary_policy = known_policy
                        break
            if primary_policy: break
            
    
    if primary_policy and primary_policy != "UNKNOWN":
        filtered_points = [p for p in retrieved_points if p.get("policy_id") == primary_policy]
       
        if not filtered_points and retrieved_points:
            
             pass
    else:
        filtered_points = retrieved_points


    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', query)
    query_year = year_match.group(1) if year_match else None
    
   
    governance_section = ""
    if policy_graph and policy_executor and primary_policy and primary_policy != "UNKNOWN":
        try:
           
            from datetime import date
            ref_date = date.today()
            if query_year:
                try:
                    ref_date = date(int(query_year), 12, 31) # End of year generally safe
                except:
                    pass
            
            
            active_clauses = policy_graph.get_active_clauses(primary_policy, ref_date)
            
            if active_clauses:
                gov_lines = [f"\n🔍 **Governance Verification ({ref_date.year})**:"]
                
              
                if demographics and len(demographics) > 0:
                    gov_lines.append("**Eligibility Logic Trace:**")
                    pass_count = 0
                    fail_count = 0
                    
                    for clause in active_clauses:
                       
                        if clause.logic:
                            
                            if "eligibility" in clause.tags:
                                passed = policy_executor.evaluate(clause.logic, demographics)
                                icon = "✅" if passed else "❌"
                            
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
                    
                    gov_lines.append("**Active Binding Rules (Verified):**")
                    for clause in active_clauses[:3]: 
                         docs = policy_graph.get_provenance_chain(clause.id)
                         source = f"{docs[0].doc_type} {docs[0].id}" if docs else "Official Rule"
                         gov_lines.append(f"- {clause.text} *[{source}]*")
                    if len(active_clauses) > 3:
                         gov_lines.append(f"*(and {len(active_clauses)-3} more active clauses)*")

                governance_section = "\n".join(gov_lines)
                
        except Exception as e:
            logger.error(f"Governance engine error: {e}")
            governance_section = f"\n*(Governance check failed: {str(e)})*"
            

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
    
  
    by_modality = {}
    for point in filtered_points:
        modality = point.get("modality", "text")
        if modality not in by_modality:
            by_modality[modality] = []
        by_modality[modality].append(point)
    
    
    sections = []
    
   
    if is_what_is and primary_policy:
        if primary_policy in POLICY_DESCRIPTIONS:
            sections.append(f"**{primary_policy}**: {POLICY_DESCRIPTIONS[primary_policy]}")
        
    
        if filtered_points:
            top = filtered_points[0]
            content = top['content_preview'][:300] if top.get('content_preview') else ""
            if content and len(content) > 50:
                sections.append(f"**Key Details**: {content}")
        
       
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
    
    
    elif is_budget:
        budget = by_modality.get("budget", [])
        if budget:
            
            if query_year:
                budget = [b for b in budget if str(b.get('year', '')) == query_year]
            
    
            seen_years = set()
            for b in budget:
                year = b.get('year', 'N/A')
                if year in seen_years:
                    continue
                seen_years.add(year)
                
                allocation = b.get('allocation_crores', 0)
                expenditure = b.get('expenditure_crores', 0)
                policy = b.get('policy_id', 'Unknown')
                
                
                if allocation > 0:
                    utilization = round((expenditure / allocation) * 100, 1) if allocation > 0 else 0
                    sections.append(
                        f"**{policy} Budget ({year})**:\n"
                        f"• Allocated: ₹{allocation:,.2f} crore\n"
                        f"• Spent: ₹{expenditure:,.2f} crore\n"
                        f"• Utilization: {utilization}%"
                    )
                else:
                
                    content = b['content_preview'][:400] if b.get('content_preview') else ""
                    sections.append(f"**Budget ({year})**: {content}")
        else:
            
            for p in filtered_points[:2]:
                sections.append(f"{p['content_preview'][:400]}")
    
   
    elif is_eligibility:
        if primary_policy in POLICY_DESCRIPTIONS:
            sections.append(f"**About {primary_policy}**: {POLICY_DESCRIPTIONS[primary_policy]}")
        sections.append("**Eligibility**: Based on your profile, you may be eligible. Use the eligibility checker or upload your Aadhaar for personalized results.")
    
  
    elif is_how_to:
        if primary_policy:
            sections.append(f"**How to Apply for {primary_policy}**:")
            sections.append(f"1. Visit the official portal: {get_application_url(primary_policy)}")
            sections.append("2. Keep your Aadhaar card and required documents ready")
            sections.append("3. Fill the application form with accurate details")
            sections.append("4. Submit and save your application reference number")
    

    else:
        
        temporal = by_modality.get("temporal") or by_modality.get("text", [])
        if temporal:
            top = temporal[0]
            content = top['content_preview'][:400] if top.get('content_preview') else ""
            sections.append(f"**{top['policy_id']} ({top.get('year', 'N/A')})**: {content}")
        
      
        budget = by_modality.get("budget", [])
        if budget:
            top = budget[0]
            content = top['content_preview'][:300] if top.get('content_preview') else ""
            sections.append(f"**Budget ({top.get('year', 'N/A')})**: {content}")
        
        
        news = by_modality.get("news", [])
        if news:
            top = news[0]
            content = top['content_preview'][:300] if top.get('content_preview') else ""
            sections.append(f"**Latest Updates ({top.get('year', 'N/A')})**: {content}")
    
    
    if not sections and filtered_points:
        top = filtered_points[0]
        sections.append(f"{top['content_preview'][:500]}")
    
    return ("\n\n".join(sections) + "\n" + governance_section) if sections else "No detailed information available."


def calculate_confidence(retrieved_points: List[Dict[str, Any]]) -> float:
   
    if not retrieved_points:
        return 0.0
    
   
    top_scores = [p.get("score", 0) for p in retrieved_points[:3]]
    base_confidence = sum(top_scores) / len(top_scores) if top_scores else 0.0
    
    
    policies = [p.get("policy_id") for p in retrieved_points[:3]]
    if len(set(policies)) == 1 and policies[0] is not None:
        base_confidence = min(base_confidence + 0.15, 1.0)
    
   
    modalities = set(p.get("modality") for p in retrieved_points[:5])
    if len(modalities) >= 2:
        base_confidence = min(base_confidence + 0.1, 1.0)
    
    return round(min(base_confidence, 1.0), 3)
