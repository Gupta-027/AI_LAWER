"""Nyaya Saathi — a simple chat: speak or type your problem, hear the advice, keep talking.

The older step-by-step case builder is still available: streamlit run detailed_app.py
"""
from __future__ import annotations

from html import escape
from pathlib import Path

from dotenv import load_dotenv
import streamlit as st

load_dotenv(Path(__file__).parent / ".env", override=False)

from nyaya.advice import get_advice, speech_text, to_audio
from nyaya.gemini import GeminiClient

st.set_page_config(page_title="न्याय साथी | Nyaya Saathi", page_icon="⚖️", layout="centered")

st.markdown("""<style>
.stApp{background:linear-gradient(180deg,#FFF4E0 0%,#FFFFFF 40%,#E9F7EF 100%);}
.block-container{max-width:780px;padding-top:1rem;}
.hero{background:linear-gradient(120deg,#FF8A00,#E52E71);color:#fff;border-radius:22px;padding:18px 16px;text-align:center;
      box-shadow:0 6px 18px rgba(229,46,113,.25);margin-bottom:10px}
.hero h1{color:#fff;font-size:2.1rem;margin:0;padding:0}
.hero p{font-size:1.15rem;margin:.3rem 0 0}
.hint{background:#E3F2FD;border-radius:14px;padding:10px 14px;font-size:1.15rem;text-align:center;margin:8px 0}
.step{font-size:1.3rem;font-weight:700;margin:14px 0 6px;color:#3B1F6E}
.card{border-radius:16px;padding:12px 16px;margin:8px 0;font-size:1.15rem;line-height:1.65;color:#1d1d1d}
.card h3{margin:0 0 4px;font-size:1.25rem;padding:0}
.card ol,.card ul{margin:0;padding-left:1.4rem}
.c-blue{background:#E3F2FD;border-left:8px solid #1E88E5}
.c-green{background:#E8F5E9;border-left:8px solid #43A047}
.c-yellow{background:#FFF8E1;border-left:8px solid #FFB300}
.c-red{background:#FFEBEE;border-left:8px solid #E53935}
.c-purple{background:#F3E5F5;border-left:8px solid #8E24AA}
.c-orange{background:#FFF3E0;border-left:8px solid #FB8C00;font-weight:600}
[data-testid="stChatMessage"]{font-size:1.15rem}
.stButton button{font-size:1.15rem !important;font-weight:700;border-radius:16px;min-height:3.2rem}
.foot{text-align:center;color:#555;font-size:.9rem;margin:18px 0 70px}
</style>""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []  # {"role", "content", ["advice", "audio", "hindi"]}


def new_chat() -> None:
    st.session_state.messages = []
    st.session_state.pop("pending", None)


top_lang, top_new = st.columns([3, 2], vertical_alignment="bottom")
with top_lang:
    lang = st.segmented_control("भाषा / Language", ["हिन्दी", "English"], default="हिन्दी", key="lang") or "हिन्दी"
hindi = lang == "हिन्दी"
T = (lambda hi, en: hi if hindi else en)
top_new.button(T("🆕 नई बातचीत", "🆕 New chat"), on_click=new_chat, width="stretch")

st.markdown(f'<div class="hero"><h1>⚖️ {T("न्याय साथी", "Nyaya Saathi")}</h1>'
            f'<p>{T("अपनी परेशानी बोलिए या लिखिए — हम आसान भाषा में रास्ता बताएँगे, और सुनाएँगे भी 🔊", "Speak or type your problem — we will tell you what to do, and read it out 🔊")}</p></div>',
            unsafe_allow_html=True)

client = GeminiClient()
if not client.configured:
    st.error(T("सर्वर पर GEMINI_API_KEY सेट नहीं है।", "GEMINI_API_KEY is not set on the server."))

# The input bar is pinned to the bottom; it clears itself after every send, so a new recording can always start.
sent = st.chat_input(T("यहाँ लिखिए, या 🎤 दबाकर बोलिए…", "Type here, or press 🎤 to speak…"),
                     accept_audio=True, disabled=not client.configured, max_chars=4000)


def respond(text: str) -> None:
    messages = st.session_state.messages
    messages.append({"role": "user", "content": text})
    with st.spinner(T("⏳ सलाह तैयार हो रही है…", "⏳ Preparing advice…")):
        history = [{"role": m["role"], "content": m["content"]} for m in messages]
        advice = get_advice(history, hindi, client)
        spoken = speech_text(advice, hindi)
        messages.append({"role": "assistant", "content": spoken, "advice": advice,
                         "audio": to_audio(spoken, hindi), "hindi": hindi})
    st.session_state.autoplay = len(messages) - 1  # play only the newest answer, once


if sent:
    text = (sent.text or "").strip()
    if sent.audio is not None:
        with st.spinner(T("👂 सुन रहे हैं…", "👂 Listening…")):
            heard = client.transcribe_audio(sent.audio.getvalue(), sent.audio.type or "audio/wav", "Hindi" if hindi else "Auto")
        if heard.ok:
            text = (text + " " + heard.text).strip()
        elif not text:
            st.warning(heard.status)
    if text:
        respond(text)
elif st.session_state.get("pending"):
    respond(st.session_state.pop("pending"))


def card(color: str, title: str, body: str) -> None:
    st.markdown(f'<div class="card {color}"><h3>{title}</h3>{body}</div>' if title else
                f'<div class="card {color}">{body}</div>', unsafe_allow_html=True)


def bullets(items: list[str], tag: str = "ul") -> str:
    return f"<{tag}>" + "".join(f"<li>{escape(x)}</li>" for x in items) + f"</{tag}>"


def show_answer(msg: dict, index: int) -> None:
    a = msg["advice"]
    R = (lambda hi, en: hi if msg["hindi"] else en)
    if msg["audio"]:
        st.audio(msg["audio"], format="audio/mp3", autoplay=st.session_state.get("autoplay") == index)
    if a["error"]:
        card("c-red", R("⚠️ अभी जवाब नहीं मिला", "⚠️ No answer right now"), escape(a["error"]))
    elif a["reply"]:
        card("c-blue", "", escape(a["reply"]))
    if a["steps"]:
        card("c-green", R("✅ आप क्या करें", "✅ What you can do"), bullets(a["steps"], "ol"))
    if a["proof"]:
        card("c-yellow", R("📂 ये सबूत संभालकर रखें", "📂 Keep this proof"), bullets(a["proof"]))
    if a["need_lawyer"] and a["lawyer_reason"]:
        card("c-red", R("👨‍⚖️ वकील से ज़रूर मिलें", "👨‍⚖️ Please see a lawyer"), escape(a["lawyer_reason"]))
    if a["helplines"]:
        card("c-purple", R("📞 मुफ़्त मदद", "📞 Free help"), bullets(a["helplines"]))
    if a["follow_up"]:
        card("c-orange", "", "❓ " + escape(a["follow_up"]))


if not st.session_state.messages:
    st.markdown(f'<div class="hint">🎤 {T("नीचे माइक दबाकर बोलिए, या लिखकर भेजिए", "Press the mic below to speak, or type and send")}</div>',
                unsafe_allow_html=True)
    st.markdown(f'<div class="step">👇 {T("या कोई एक चुनिए", "Or pick one")}</div>', unsafe_allow_html=True)
    examples = [
        ("🏠", T("मकान मालिक जमा राशि नहीं लौटा रहा", "Landlord not returning deposit"),
         T("मैंने किराए का घर खाली कर दिया, मकान मालिक मेरी 15000 रुपये जमा राशि वापस नहीं कर रहा।", "I vacated my rented house but the landlord is not returning my ₹15,000 deposit.")),
        ("💰", T("तनख्वाह नहीं मिली", "Salary not paid"),
         T("मेरे मालिक ने दो महीने से मेरी तनख्वाह नहीं दी है।", "My employer has not paid my salary for two months.")),
        ("📦", T("ऑनलाइन सामान का पैसा वापस नहीं आया", "Online refund not received"),
         T("मैंने ऑनलाइन सामान लौटाया, पर 3 हफ़्ते से पैसा वापस नहीं आया।", "I returned an online order 3 weeks ago but the refund has not come.")),
        ("📄", T("नोटिस आया है, समझ नहीं आ रहा", "Got a notice I don't understand"),
         T("मुझे एक कानूनी नोटिस आया है, मुझे समझ नहीं आ रहा क्या करूँ।", "I received a legal notice and do not understand what to do.")),
    ]
    cols = st.columns(2)
    for i, (icon, label, story) in enumerate(examples):
        if cols[i % 2].button(f"{icon} {label}", width="stretch", key=f"ex{i}", disabled=not client.configured):
            st.session_state.pending = story
            st.rerun()
else:
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"], avatar="🙋" if msg["role"] == "user" else "⚖️"):
            if msg["role"] == "user":
                st.write(msg["content"])
            else:
                show_answer(msg, i)
    st.session_state.pop("autoplay", None)  # later reruns (e.g. language switch) don't replay audio

st.markdown(f'<div class="foot">{T("यह ऐप वकील नहीं है — सिर्फ़ शुरुआती सलाह देता है। कोर्ट, पुलिस या नोटिस वाले मामलों में वकील से ज़रूर मिलें।", "This app is not a lawyer — it gives a first suggestion only. For court, police or notice matters, see a lawyer.")}</div>',
            unsafe_allow_html=True)
