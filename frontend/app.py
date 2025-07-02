import requests
import streamlit as st

# -- Config --------
BACKEND_URL = "http://localhost:8000/analyze/"
st.set_page_config(page_title="SplitMate", layout="centered", initial_sidebar_state="collapsed")

# -- Custom CSS 


# -- Layout ------------------
st.markdown('<div class="card">', unsafe_allow_html=True)

st.title("SplitMate")
st.caption("Split receipts with the power of an LLM!")

# -- Upload and Scan Tabs ---------------
st.markdown("### Upload or Scan your receipt")
tab_upload, tab_scan = st.tabs(["Upload file", "Scan with camera"])

uploaded_file = None
camera_image = None

with tab_upload:
    uploaded_file = st.file_uploader(
        "Choose a JPEG / PNG / PDF",
        type=["jpg", "jpeg", "png", "pdf"],
        label_visibility="collapsed",
    )

with tab_scan:
    if st.checkbox("Enable camera"):
        camera_image = st.camera_input("Take a photo")

# -- Participant Inputs -------------------
with st.expander("Participants"):
    names = st.text_input("Comma-separated names", value="George, Alice, Bob")

with st.expander("Special Instructions"):
    instruction = st.text_area(
        "How should we split it?",
        value="George only split 20% of the gift and Bob and I paid the rest evenly.",
        height=100,
    )

# -- Analyze Button ------------------------
clicked = st.button(
    "Analyze",
    use_container_width=True,
    disabled=not (uploaded_file or camera_image),
)

# -- Processing -----------------------------
if clicked:
    with st.spinner("Analyzing your receipt…"):
        file_bytes = (
            uploaded_file.read() if uploaded_file
            else camera_image.getvalue() if camera_image
            else None
        )
        if not file_bytes:
            st.error("Please upload or scan a receipt.")
            st.stop()

        try:
            res = requests.post(
                BACKEND_URL,
                files={"file": file_bytes},
                data={"instruction": instruction, "names": names},
                timeout=120,
            )
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            st.error(f"Backend error: {e}")
            st.stop()

    # -- Parsed Items ---------------------------
    parsed = data.get("parsed", {})
    st.subheader("Parsed Items")
    if not parsed.get("items"):
        st.warning("No line-items detected; using total only.")
    else:
        for item in parsed["items"]:
            st.markdown(f"- `{item['name']}` — **${item['price']:.2f}**")
        st.markdown(
            f"**Tax**: ${parsed['tax']:.2f} &nbsp;|&nbsp; "
            f"**Total**: ${parsed['total']:.2f}",
            unsafe_allow_html=True,
        )

    # -- Suggested Split -------------------------
    suggestion = data.get("suggestion", {})
    st.subheader("Suggested Split")

    if "allocation" in suggestion:
        cols = st.columns(len(suggestion["allocation"]))
        for i, (person, amt) in enumerate(suggestion["allocation"].items()):
            with cols[i]:
                st.markdown(
                    f"**{person}**<br><span style='font-size:1.5em;'>${amt:,.2f}</span>",
                    unsafe_allow_html=True,
                )
    else:
        st.text(suggestion.get("raw", "No allocation returned."))

    # -- Breakdown ------------------------
    if "breakdown" in suggestion:
        st.subheader("Breakdown")
        b = suggestion["breakdown"]
        st.markdown(f"""
        - Subtotal: **${b.get('subtotal', 0):.2f}**
        - Tax: **${b.get('tax', 0):.2f}**
        - Tip: **${b.get('tip', 0):.2f}**
        - Total: **${b.get('total', 0):.2f}**
        """)

    # -- Item Mapping ----------------------
    if "item_mapping" in suggestion:
        st.subheader("Item Mapping")
        for person, items in suggestion["item_mapping"].items():
            with st.expander(person):
                for item in items:
                    st.markdown(f"- `{item['name']}` — **${item['price']:.2f}**")

    # -- Summary ------------------
    if "summary" in suggestion:
        st.success(suggestion["summary"])

# --- Close Layout ---------------
st.markdown('</div>', unsafe_allow_html=True)
