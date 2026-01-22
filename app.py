import streamlit as st
import requests
import json
from datetime import datetime
import re
from requests.exceptions import Timeout, ConnectionError, HTTPError
import os
import io

# Imports for Multimodality
try:
    import speech_recognition as sr
    import av  # PyAV for in-memory video processing
except ImportError:
    st.error("⚠️ Please install missing packages: pip install SpeechRecognition av")

# pg config
st.set_page_config(
    page_title="PolicyPulse",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# css
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# session vars
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'uploaded_docs' not in st.session_state:
    st.session_state.uploaded_docs = []

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def api_call(endpoint, method="GET", data=None):
    """call api with error handling"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            resp = requests.get(url, timeout=TIMEOUT)
        else:
            resp = requests.post(url, json=data, timeout=TIMEOUT)
        
        resp.raise_for_status()
        return resp.json(), None
    
    except Timeout:
        return None, "⏱️ Timeout - server took too long"
    except ConnectionError:
        return None, "❌ Can't connect to API. Is server running?"
    except HTTPError as e:
        if e.response.status_code == 400:
            err = e.response.json().get('detail', 'Bad request')
            return None, f"⚠️ {err}"
        elif e.response.status_code == 422:
            return None, "⚠️ Validation error - check your input"
        elif e.response.status_code == 429:
            return None, "🚫 Rate limit exceeded - wait a bit"
        else:
            return None, f"❌ Error {e.response.status_code}"
    except Exception as e:
        return None, f"❌ {str(e)}"

def detect_policy(query):
    """detect policy from keywords"""
    q = query.lower()
    
    # check keywords
    if any(w in q for w in ["rti", "right to information", "transparency"]):
        return "RTI"
    if any(w in q for w in ["nrega", "mgnrega", "rural employment"]):
        return "NREGA"
    if any(w in q for w in ["nep", "education policy", "curriculum"]):
        return "NEP"
    if any(w in q for w in ["pm kisan", "farmer", "6000"]):
        return "PM-KISAN"
    if any(w in q for w in ["swachh", "clean india", "toilet"]):
        return "SWACHH-BHARAT"
    if any(w in q for w in ["digital india", "upi", "aadhaar"]):
        return "DIGITAL-INDIA"
    if any(w in q for w in ["ayushman", "health coverage", "insurance"]):
        return "AYUSHMAN-BHARAT"
    if any(w in q for w in ["make in india", "manufacturing", "pli"]):
        return "MAKE-IN-INDIA"
    if any(w in q for w in ["skill india", "training", "pmkvy"]):
        return "SKILL-INDIA"
    if any(w in q for w in ["smart city", "iot", "urban"]):
        return "SMART-CITIES"
    
    return "NREGA"  # default

def detect_policy_content(txt):
    """find policy from doc content"""
    txt = txt.lower()
    
    scores = {}
    keywords = {
        "AYUSHMAN-BHARAT": ["ayushman", "health coverage", "5 lakh"],
        "MAKE-IN-INDIA": ["make in india", "manufacturing", "atmanirbhar"],
        "SKILL-INDIA": ["skill india", "pmkvy", "vocational"],
        "SMART-CITIES": ["smart city", "iot", "command center"],
        "NREGA": ["nrega", "employment guarantee", "100 days"],
        "RTI": ["rti", "right to information"],
        "NEP": ["education policy", "curriculum"],
        "PM-KISAN": ["pm kisan", "farmer income"],
        "SWACHH-BHARAT": ["swachh", "toilet", "sanitation"],
        "DIGITAL-INDIA": ["digital india", "upi"]
    }
    
    for pol, words in keywords.items():
        scores[pol] = sum(1 for w in words if w in txt)
    
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "NREGA"

def extract_year(content, fname):
    """get year from content or filename"""
    # try filename
    match = re.search(r'(20\d{2})', fname)
    if match:
        return match.group(1)
    
    # try content
    years = re.findall(r'\b(20\d{2})\b', content[:800])
    if years:
        return max(years)
    
    return str(datetime.now().year)

# header
st.markdown('<h1 style="color:#1E88E5">🔍 PolicyPulse</h1>', unsafe_allow_html=True)
st.caption("AI-Powered Policy Evolution Analysis")

# tabs
tab = st.radio(
    "Module",
    ["💬 Chat", "📈 Drift", "📄 Upload", "🎯 Recommendations", "⚙️ Advanced"],
    horizontal=True,
    label_visibility="collapsed"
)

# CHAT TAB
if tab == "💬 Chat":
    st.markdown("### 🗣️ Query Policies")
    st.caption("Auto-detects policy from your question")
    
    # show history
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant"):
                if "policy" in msg:
                    st.caption(f"🔍 **{msg['policy']}**")
                st.markdown(msg["content"])
                
                if "evidence" in msg and msg["evidence"]:
                    with st.expander("📊 Evidence"):
                        for i, ev in enumerate(msg["evidence"], 1):
                            st.markdown(f"**{i}. {ev['year']} ({ev['modality']})**")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Score", f"{ev['score']:.3f}")
                            with col2:
                                st.metric("Weight", f"{ev['decay_weight']:.2f}")
                            with col3:
                                st.metric("Access", ev['access_count'])
                            st.info(ev['preview'][:150] + "...")
                            if i < len(msg["evidence"]):
                                st.divider()

# DRIFT TAB
elif tab == "📈 Drift":
    st.markdown("### 📊 Drift Analysis")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.caption("Track policy evolution over time")
    with col2:
        pol = st.selectbox("Policy", 
            ["NREGA", "RTI", "NEP", "PM-KISAN", "SWACHH-BHARAT", 
             "DIGITAL-INDIA", "AYUSHMAN-BHARAT", "MAKE-IN-INDIA", 
             "SKILL-INDIA", "SMART-CITIES"])
    with col3:
        mod = st.selectbox("Modality", ["text", "budget", "news"])
    
    if st.button("🔍 Analyze", use_container_width=True):
        with st.spinner("Computing..."):
            data, err = api_call("/drift", "POST", 
                {"policy_id": pol, "modality": mod})
            
            if err:
                st.error(err)
            elif data:
                if "error" in data:
                    st.warning(data["error"])
                else:
                    # metrics
                    if data.get("max_drift"):
                        md = data["max_drift"]
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.metric("Max Drift Period", 
                                f"{md['from_year']} → {md['to_year']}")
                        with c2:
                            st.metric("Drift Score", 
                                f"{md['drift_score']:.3f}")
                        with c3:
                            st.metric("Total Periods", 
                                data.get("total_periods", 0))
                        
                        st.divider()
                    
                    # timeline
                    timeline = data.get("timeline", [])
                    if timeline:
                        st.markdown("### Timeline")
                        for p in timeline:
                            icon = {"HIGH": "🔴", "MEDIUM": "🟡", 
                                   "LOW": "🟢"}.get(p["severity"], "⚪")
                            st.markdown(
                                f"{icon} **{p['from_year']} → {p['to_year']}** | "
                                f"Score: **{p['drift_score']:.3f}** | "
                                f"{p['severity']}"
                            )
                            st.divider()

# UPLOAD TAB  
elif tab == "📄 Upload":
    st.markdown("### 📤 Upload Documents & Media")
    st.caption("Auto-detects policy from Text, Image, Audio, or Video")
    
    file = st.file_uploader("Upload File", 
        type=["txt", "pdf", "jpg", "jpeg", "png", "mp3", "wav", "mp4", "avi", "mkv"])
    
    content = ""

    if file:
        st.info(f"📄 **{file.name}** ({file.size} bytes)")
        try:
            # IMAGE PROCESSING
            if file.type in ["image/jpeg", "image/png", "image/jpg"]:
                from PIL import Image
                import pytesseract
                image = Image.open(file)
                content = pytesseract.image_to_string(image)
                st.success("✅ OCR Extraction Complete")
            
            # AUDIO PROCESSING
            elif file.type in ["audio/mpeg", "audio/wav", "audio/mp3"]:
                with st.spinner("🎧 Transcribing Audio..."):
                    r = sr.Recognizer()
                    # AudioFile supports file-like objects (BytesIO)
                    with sr.AudioFile(file) as source:
                        audio_data = r.record(source)
                        content = r.recognize_google(audio_data)
                    st.success("✅ Audio Transcription Complete")

            # VIDEO PROCESSING (In-Memory / PyAV Method)
            elif file.type in ["video/mp4", "video/x-msvideo", "video/quicktime", "video/x-matroska"]:
                with st.spinner("🎬 Extracting & Transcribing Video..."):
                    try:
                        # 1. Open video stream directly from RAM
                        # file.read() gives bytes, io.BytesIO makes it a file-like object for PyAV
                        file.seek(0) # Reset pointer just in case
                        container = av.open(io.BytesIO(file.read()))
                        
                        # 2. Find audio stream
                        audio_stream = next((s for s in container.streams if s.type == 'audio'), None)
                        
                        if audio_stream:
                            # 3. Create a memory buffer for the WAV file
                            wav_buffer = io.BytesIO()
                            
                            # 4. Create an output container (WAV) writing to that buffer
                            output_container = av.open(wav_buffer, 'w', format='wav')
                            output_stream = output_container.add_stream('pcm_s16le', rate=16000, layout='mono')
                            
                            # 5. Decode and Resample
                            for frame in container.decode(audio_stream):
                                for packet in output_stream.encode(frame):
                                    output_container.mux(packet)
                            
                            # Flush
                            for packet in output_stream.encode(None):
                                output_container.mux(packet)
                            
                            output_container.close()
                            
                            # 6. Transcribe from the WAV buffer
                            wav_buffer.seek(0) # Rewind buffer
                            r = sr.Recognizer()
                            with sr.AudioFile(wav_buffer) as source:
                                audio_data = r.record(source)
                                content = r.recognize_google(audio_data)
                                
                            st.success("✅ Video Transcription Complete")
                        else:
                            st.warning("⚠️ No audio track found in this video.")
                            
                    except Exception as e:
                        st.error(f"Processing Error: {str(e)}")

            # TEXT PROCESSING
            else:
                # read content
                if file.type == "text/plain":
                    content = file.read().decode("utf-8")
                else:
                    content = file.read().decode("utf-8", errors="ignore")
            
            # PREVIEW AND DETECT (Common for all types)
            if content:
                with st.expander("Extracted Content Preview"):
                    st.text(content[:400] + "..." if len(content) > 400 else content)
                
                st.markdown("---")
                st.markdown("#### Auto-Detection")
                pol = detect_policy_content(content)
                yr = extract_year(content, file.name)
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Policy", pol)
                with c2:
                    st.metric("Year", yr)
                
                st.markdown("#### Override (optional)")
                c1, c2, c3 = st.columns(3)
                with c1:
                    manual_pol = st.selectbox("Policy", 
                        ["AUTO", "NREGA", "RTI", "NEP", "PM-KISAN", 
                         "SWACHH-BHARAT", "DIGITAL-INDIA", "AYUSHMAN-BHARAT",
                         "MAKE-IN-INDIA", "SKILL-INDIA", "SMART-CITIES"])
                with c2:
                    manual_yr = st.text_input("Year", value=yr)
                with c3:
                    modality = st.selectbox("Type", ["text", "news", "amendment", "speech", "hearing"])
                
                final_pol = pol if manual_pol == "AUTO" else manual_pol
                final_yr = manual_yr or yr
                
                st.markdown("---")
                if st.button("⚡ INGEST", use_container_width=True, type="primary"):
                    with st.spinner(f"Ingesting into {final_pol}..."):
                        result, err = api_call("/ingest-document", "POST", {
                            "policy_id": final_pol,
                            "content": content,
                            "year": final_yr,
                            "modality": modality,
                            "filename": file.name
                        })
                        if err:
                            st.error(err)
                        elif result:
                            st.success(f"✅ Ingested {result['chunks_added']} chunks!")
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                st.metric("Policy", result['policy_id'])
                            with c2:
                                st.metric("Chunks", result['chunks_added'])
                            with c3:
                                st.metric("Year", result.get('year', 'N/A'))
                            with st.expander("Chunks Preview"):
                                for i, chunk in enumerate(result.get('chunks_preview', [])[:3], 1):
                                    st.markdown(f"**Chunk {i}:** {chunk[:180]}...")
                                    st.divider()
            else:
                if not file.type.startswith("video") and not file.type.startswith("audio"):
                    st.warning("⚠️ Could not extract text from this file.")

        except Exception as e:
            st.error(f"❌ Error during processing: {str(e)}")
    else:
        st.info("👆 Upload a document, image, audio, or video to start")

# RECOMMENDATIONS TAB
elif tab == "🎯 Recommendations":
    st.markdown("### 🎯 Policy Recommendations")
    st.caption("Discover related policies and actionable insights")
    
    # Preset recommendation queries
    st.markdown("**Quick Actions:**")
    col1, col2, col3 = st.columns(3)
    
    preset_query = None
    with col1:
        if st.button("📊 Find Related Policies", use_container_width=True):
            preset_query = "related"
    with col2:
        if st.button("⚠️ Identify Conflicts", use_container_width=True):
            preset_query = "conflicts"
    with col3:
        if st.button("💡 Priority Areas", use_container_width=True):
            preset_query = "priority"
    
    st.markdown("---")
    
    # Policy selector
    col1, col2 = st.columns([2, 1])
    with col1:
        pol_rec = st.selectbox("Select Policy to Analyze",
            ["NREGA", "RTI", "NEP", "PM-KISAN", "SWACHH-BHARAT",
             "DIGITAL-INDIA", "AYUSHMAN-BHARAT", "MAKE-IN-INDIA",
             "SKILL-INDIA", "SMART-CITIES"],
            key="rec_policy")
    with col2:
        year_rec = st.number_input("Year (Optional)", 
            min_value=2000, max_value=2026, value=None, 
            step=1, key="rec_year",
            help="Leave empty to search across all years")
    
    top_k_rec = st.slider("Number of Recommendations", 1, 10, 5, key="rec_top_k")
    
    if st.button("🔍 Get Recommendations", type="primary", use_container_width=True) or preset_query:
        with st.spinner(f"Finding recommendations for {pol_rec}..."):
            # Build request payload
            payload = {
                "policy_id": pol_rec,
                "top_k": top_k_rec
            }
            if year_rec:
                payload["year"] = int(year_rec)
            
            data, err = api_call("/recommendations", "POST", payload)
            
            if err:
                st.error(err)
            elif data:
                recommendations = data.get("recommendations", [])
                count = data.get("count", 0)
                
                if count == 0:
                    st.warning(f"No related policies found for {pol_rec}. Try a different policy or remove year filter.")
                else:
                    st.success(f"✅ Found {count} related policies")
                    
                    # Display recommendations
                    st.markdown("### 📋 Related Policies")
                    
                    for i, rec in enumerate(recommendations, 1):
                        with st.container():
                            # Header with policy info
                            col1, col2, col3 = st.columns([2, 1, 1])
                            with col1:
                                st.markdown(f"**{i}. {rec['policy_id']}**")
                            with col2:
                                st.metric("Year", rec.get('year', 'N/A'))
                            with col3:
                                similarity = rec.get('similarity_score', 0)
                                st.metric("Similarity", f"{similarity:.3f}")
                            
                            # Sample text preview
                            sample = rec.get('sample_text', '')
                            if sample:
                                st.info(sample)
                            
                            # Actionable recommendations based on similarity
                            if similarity > 0.85:
                                st.markdown("**🎯 Recommended Action:**")
                                st.markdown(f"🔴 **HIGH PRIORITY**: Review {rec['policy_id']} alongside {pol_rec} for potential conflicts or redundancies")
                            elif similarity > 0.70:
                                st.markdown("**🎯 Recommended Action:**")
                                st.markdown(f"🟡 **MEDIUM PRIORITY**: Cross-reference {rec['policy_id']} for complementary provisions with {pol_rec}")
                            else:
                                st.markdown("**🎯 Recommended Action:**")
                                st.markdown(f"🟢 **LOW PRIORITY**: Consider {rec['policy_id']} for best practices that could inform {pol_rec}")
                            
                            if i < count:
                                st.divider()
                    
                    # Summary recommendations
                    if preset_query == "conflicts":
                        st.markdown("---")
                        st.markdown("### ⚠️ Conflict Analysis")
                        high_sim = [r for r in recommendations if r.get('similarity_score', 0) > 0.85]
                        if high_sim:
                            st.warning(f"Found {len(high_sim)} policies with high similarity (>0.85). These may have overlapping provisions that require review.")
                        else:
                            st.info("No high-similarity conflicts detected.")
                    
                    elif preset_query == "priority":
                        st.markdown("---")
                        st.markdown("### 💡 Priority Recommendations")
                        st.markdown(f"**For {pol_rec}:**")
                        st.markdown(f"- Review the top {min(3, count)} related policies for alignment")
                        st.markdown(f"- Focus on high-similarity policies (>0.85) for conflict resolution")
                        st.markdown(f"- Use medium-similarity policies (0.70-0.85) for policy enhancement")

# ADVANCED TAB
elif tab == "⚙️ Advanced":
    st.markdown("### ⚙️ Advanced")
    
    pol = st.selectbox("Policy", 
        ["NREGA", "RTI", "NEP", "PM-KISAN", "SWACHH-BHARAT",
         "DIGITAL-INDIA", "AYUSHMAN-BHARAT", "MAKE-IN-INDIA",
         "SKILL-INDIA", "SMART-CITIES"])
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("#### ⏰ Memory Decay")
        st.caption("Apply time decay")
        
        if st.button("Apply Decay"):
            with st.spinner("Processing..."):
                result, err = api_call("/memory/decay", "POST", 
                    {"policy_id": pol})
                
                if err:
                    st.error(err)
                elif result:
                    st.success(f"✅ Updated {result['points_updated']} points")
    
    with c2:
        st.markdown("#### 💾 Export")
        st.caption("Download chat history")
        
        if st.button("Prepare Export"):
            if st.session_state.chat_history:
                data = json.dumps(st.session_state.chat_history, indent=2)
                st.download_button(
                    "📥 Download",
                    data,
                    file_name=f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            else:
                st.warning("No chat history")
    
    st.divider()
    st.markdown("#### 📊 Stats")
    
    stats, err = api_call("/stats", "GET")
    
    if err:
        st.warning(err)
    elif stats:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Points", stats.get("total_points", 0))
        with c2:
            st.metric("Dimension", stats.get("vector_dim", 0))
        with c3:
            st.metric("Distance", stats.get("distance", "COSINE"))
        
        if "policy_breakdown" in stats:
            st.markdown("#### Policy Breakdown")
            breakdown = stats["policy_breakdown"]
            items = list(breakdown.items())
            mid = len(items) // 2
            
            c1, c2 = st.columns(2)
            with c1:
                for p, cnt in items[:mid]:
                    st.metric(p, cnt)
            with c2:
                for p, cnt in items[mid:]:
                    st.metric(p, cnt)
    
    # NEW: Performance Metrics Section
    st.divider()
    st.markdown("#### ⚡ Performance Metrics")
    
    perf, perf_err = api_call("/performance", "GET")
    
    if perf_err:
        st.info("Performance tracking unavailable")
    elif perf:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            avg_query = perf.get("average_query_time_ms", 0)
            st.metric("Avg Query Time",  f"{avg_query:.0f}ms")
        with c2:
            total_ops = perf.get("total_queries", 0) + perf.get("total_drifts", 0) + perf.get("total_recommendations", 0)
            st.metric("Total Operations", total_ops)
        with c3:
            throughput = perf.get("operations_per_minute", 0)
            st.metric("Throughput", f"{throughput:.1f}/min")
        with c4:
            uptime = perf.get("uptime_seconds", 0)
            st.metric("Uptime", f"{int(uptime//60)}m {int(uptime%60)}s")
        
        # Show detailed breakdown in expander
        with st.expander("📈 Detailed Performance"):
            st.markdown(f"**Query Performance:**")
            st.write(f"- Average: {perf.get('average_query_time_ms', 0):.2f}ms")
            st.write(f"- Min: {perf.get('min_query_time_ms', 0):.2f}ms")
            st.write(f"- Max: {perf.get('max_query_time_ms', 0):.2f}ms")
            st.write(f"- Count: {perf.get('total_queries', 0)}")
            
            st.markdown(f"**Recommendations Performance:**")
            st.write(f"- Average: {perf.get('average_recommendation_time_ms', 0):.2f}ms")
            st.write(f"- Count: {perf.get('total_recommendations', 0)}")
    
    if st.button("🗑️ Clear History"):
        st.session_state.chat_history = []
        st.success("Cleared!")
        st.rerun()

# CHAT INPUT
if tab == "💬 Chat":
    user_q = st.chat_input('Try: "What was NREGA budget in 2010?"')
    
    if user_q:
        pol = detect_policy(user_q)
        
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_q
        })
        
        with st.spinner(f"Searching {pol}..."):
            result, err = api_call("/query", "POST", {
                "policy_id": pol,
                "question": user_q,
                "top_k": 3
            })
            
            if err:
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": err,
                    "policy": pol
                })
            elif result:
                answer = result.get("final_answer", "No answer")
                
                evidence = []
                for pt in result.get("retrieved_points", [])[:3]:
                    evidence.append({
                        "year": pt.get("year"),
                        "modality": pt.get("modality"),
                        "score": pt.get("score", 0),
                        "preview": pt.get("content_preview", ""),
                        "decay_weight": pt.get("decay_weight", 1.0),
                        "access_count": pt.get("access_count", 0)
                    })
                
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": answer,
                    "evidence": evidence,
                    "policy": pol
                })
        
        st.rerun()

# footer
st.divider()
st.caption("🔍 PolicyPulse v1.0")