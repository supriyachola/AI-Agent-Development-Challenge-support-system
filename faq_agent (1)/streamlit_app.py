# app.py
import streamlit as st
from pathlib import Path
import re
import json
import time
from modules.faq import (
    answer_question,
    get_faqs_by_tag,
    get_all_tags,
    top_asked,
    log_escalation,
)

# ---------- BASIC CONFIG ----------
st.set_page_config(page_title="FAQ Assistant", layout="wide")
if "query_input" not in st.session_state:
    st.session_state["query_input"] = ""

# ---------- SIMPLE CSS ----------
st.markdown("""
<style>
.card {
    border-radius: 10px;
    padding: 14px;
    margin-top: 15px;
    background: #ffffff11;
    border: 1px solid #ffffff22;
}
.tag { 
    font-size: 0.8rem; 
    background: #eaf0ff; 
    padding: 3px 8px; 
    border-radius: 6px; 
    margin-right: 6px;
}

/* Floating Mic */
.floating-mic {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: #0b5cff;
    width: 55px;
    height: 55px;
    border-radius: 50%;
    display:flex;
    justify-content:center;
    align-items:center;
    color:white;
    font-size:26px;
    cursor:pointer;
    z-index:9999;
    transition: 0.15s ease-in-out;
}
.floating-mic:hover {
    transform: scale(1.12);
    box-shadow: 0px 6px 18px rgba(0,0,0,0.4);
}
@keyframes pulse {
  0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(11,92,255,0.4); }
  70% { transform: scale(1.05); box-shadow: 0 0 0 18px rgba(11,92,255,0); }
  100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(11,92,255,0); }
}
.mic-active {
    animation: pulse 1.3s infinite;
}
</style>
""", unsafe_allow_html=True)

# Floating mic + minimal Web Speech API
st.markdown("""
<div id="micBtn" class="floating-mic" onclick="startVoice()">🎤</div>
<script>
function startVoice(){
    const btn = document.getElementById("micBtn");
    btn.classList.add("mic-active");
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR){ alert("Voice not supported. Use Chrome/Edge."); btn.classList.remove("mic-active"); return; }
    const recog = new SR();
    recog.lang = "en-US";
    recog.interimResults = false;
    recog.onresult = e => {
        const text = e.results[0][0].transcript;
        const box = window.parent.document.querySelector('input[type="text"]');
        if (box){
            box.value = text;
            box.dispatchEvent(new Event("input", { bubbles:true }));
        }
        btn.classList.remove("mic-active");
    };
    recog.onerror = () => { btn.classList.remove("mic-active"); };
    recog.start();
}
</script>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.title("FAQ Support Assistant")
st.caption("Ask questions — clean, reliable. Category badges, copy, mic & persisted stats.")

# ---------- CATEGORY TABS ----------
tags = get_all_tags()
tabs = ["All"] + tags
tab_pages = st.tabs(tabs)

for tab_name, tab in zip(tabs, tab_pages):
    with tab:
        faqs = get_faqs_by_tag(None if tab_name == "All" else tab_name)
        if faqs:
            cols = st.columns(3)
            for i, f in enumerate(faqs[:6]):  # show up to 6 suggestions per tab
                with cols[i % 3]:
                    if st.button(f["question"], key=f"suggest_{tab_name}_{i}"):
                        st.session_state["query_input"] = f["question"]

# ---------- ASK INPUT ----------
query = st.text_input("Enter question", value=st.session_state["query_input"])
ask = st.button("Ask")

# ---------- SUMMARY HELPER ----------
def short_summary(text, max_len=150):
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_len:
        return text
    cut = text.rfind(" ", 0, max_len)
    if cut == -1:
        cut = max_len
    return text[:cut] + "..."

# ---------- ANSWER DISPLAY ----------
if ask and query.strip():
    # call answer_question robustly
    res = answer_question(query)
    # Normalize return (answer, matched, confidence, resolution)
    if isinstance(res, (list, tuple)):
        answer = res[0] if len(res) > 0 else ""
        matched = res[1] if len(res) > 1 else None
        confidence = res[2] if len(res) > 2 else 0.0
        resolution = res[3] if len(res) > 3 else "escalate"
    else:
        answer = str(res)
        matched = None
        confidence = 0.0
        resolution = "escalate"

    # small deliberate delay (feels like "responding lately")
    time.sleep(1.0)

    # show UI
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(f"**Q:** {query}")

    # category badge (prefer explicit category)
    category = None
    if isinstance(matched, dict):
        category = matched.get("category")
        if not category:
            tags_lower = [t.lower() for t in matched.get("tags", [])]
            if "sales" in tags_lower or "sale" in tags_lower:
                category = "sales"
            elif "marketing" in tags_lower:
                category = "marketing"
            elif "support" in tags_lower:
                category = "support"
            elif "billing" in tags_lower:
                category = "billing"
            elif "technical" in tags_lower:
                category = "technical"
            else:
                category = "general"
    if category:
        st.markdown(f"<div style='margin:6px 0'><strong>Category:</strong> <span style='background:#eef; padding:4px 8px; border-radius:6px;'>{category.capitalize()}</span></div>", unsafe_allow_html=True)

    # summary
    summary = short_summary(answer)
    st.markdown(f"**Summary:** {summary}")

    # safe JS for copy
    safe = json.dumps(answer)
    st.markdown(f"<button onclick='navigator.clipboard.writeText({safe})'>Copy answer</button>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    # full answer
    st.write(answer)

    # tags + confidence
    if matched:
        st.caption(f"Matched FAQ — confidence: **{confidence:.3f}**  ·  resolution: **{resolution}**")
    else:
        st.caption(f"Resolution: **{resolution}**")

    # if escalate, provide an 'Escalate' button which logs escalation
    if resolution == "escalate":
        if st.button("Escalate to human", key="escalate_btn"):
            # write escalation log using module API
            log_escalation(question=query, context=None, matched=matched, confidence=confidence, tags=(matched.get("tags") if matched else []))
            st.success("Escalation logged. Support will review it.")

    st.markdown("</div>", unsafe_allow_html=True)

# ---------- MOST ASKED (compact) ----------
st.markdown("---")
st.subheader("Most Asked FAQs")
top = top_asked(10)
if top:
    for q, c in top:
        st.write(f"**{q}** — {c}×")
else:
    st.write("No questions tracked yet.")
