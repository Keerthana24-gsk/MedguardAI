import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from agents.orchestrator import stage1, stage2

load_dotenv()
st.set_page_config(page_title="MediGuard AI", page_icon="💊", layout="wide")
st.title("💊 MediGuard AI")
st.caption("Medication Safety Assistant · informational only, not medical advice")
st.warning("OCR may misread handwritten medicine names. Verify every medicine, ingredient, strength and formulation against the original prescription before analysis.")

s = st.session_state
t1, t2, t3, t4 = st.tabs(["1 · Upload", "2 · Verify medicines", "3 · Safety analysis", "4 · Report"])

with t1:
    files = st.file_uploader("Upload prescription images", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    manual = st.text_area("Or type medicines, one per line (e.g. Crocin 500 mg BD)")
    src = st.text_input("Prescriber label for typed entries", "Manual")
    if st.button("Extract medicine candidates", type="primary"):
        if not files and not manual.strip():
            st.error("Upload at least one prescription image or enter a medicine manually.")
        else:
            with st.spinner("Reading prescription and preparing medicine candidates…"):
                s.state = stage1({
                    "files": [(f.name, f.getvalue()) for f in files],
                    "manual": [line for line in manual.splitlines() if line.strip()],
                    "manual_source": src,
                })
                s.pop("done", None)
            st.success("Candidate extraction finished. Open tab 2 and verify every entry.")

with t2:
    if "state" not in s:
        st.info("Start by uploading a prescription in tab 1.")
    else:
        state = s.state
        for warning in state.get("warnings", []):
            st.warning(warning)

        st.subheader("Original prescription images")
        if state.get("files"):
            for filename, image_bytes in state["files"]:
                with st.expander(f"View original: {filename}", expanded=True):
                    st.image(image_bytes, caption="Compare every extracted medicine with this original image.", use_container_width=True)
        else:
            st.info("No image uploaded; entries were typed manually.")

        st.subheader("Review and correct extracted medicine candidates")
        if not state.get("meds"):
            st.error("No medicine candidates were extracted. Please type the medicine names manually or upload a clearer image.")
        else:
            rows = []
            for med in state["meds"]:
                rows.append({
                    "name": med.get("name", ""),
                    "strength": med.get("strength") or "",
                    "frequency": med.get("frequency") or "",
                    "ingredients": "; ".join(med.get("ingredients", [])),
                    "formulation": med.get("formulation", ""),
                    "source": med.get("source", ""),
                    "raw_ocr_text": med.get("raw_text", ""),
                    "ocr_engine": med.get("ocr_engine", ""),
                    "match_status": med.get("match_status", ""),
                    "confirmed": False,
                })
            df = pd.DataFrame(rows)
            st.caption("Correct the name, ingredient, strength and formulation by comparing with the prescription. Tick Confirmed only after a person has checked the original writing. Unconfirmed rows are excluded from safety analysis.")
            edited = st.data_editor(
                df,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                disabled=["source", "raw_ocr_text", "ocr_engine", "match_status"],
                column_config={
                    "confirmed": st.column_config.CheckboxColumn("Human confirmed", help="Tick only after checking the original prescription."),
                    "ingredients": st.column_config.TextColumn("Active ingredient(s)", help="Separate multiple ingredients with semicolons."),
                },
                key="medicine_review_editor",
            )
            if st.button("Confirm reviewed entries & run safety analysis", type="primary"):
                confirmed_meds = []
                for _, row in edited.iterrows():
                    name = str(row.get("name", "")).strip()
                    if not name:
                        continue
                    ingredients = [part.strip().lower() for part in str(row.get("ingredients", "") or "").split(";") if part.strip()]
                    is_confirmed = bool(row.get("confirmed", False))
                    if is_confirmed and not ingredients:
                        st.error(f"Add/verify the active ingredient for '{name}' before confirming it.")
                        st.stop()
                    confirmed_meds.append({
                        "name": name,
                        "strength": str(row.get("strength", "")).strip() or None,
                        "frequency": str(row.get("frequency", "")).strip() or None,
                        "source": str(row.get("source", "Manual")).strip() or "Manual",
                        "raw_text": str(row.get("raw_ocr_text", "")),
                        "ocr_engine": str(row.get("ocr_engine", "Manual")),
                        "ingredients": ingredients,
                        "class": "",
                        "confidence": 0.0,
                        "confirmed": is_confirmed,
                        "match_status": str(row.get("match_status", "")),
                    })
                state["meds"] = confirmed_meds
                if not any(m["confirmed"] for m in confirmed_meds):
                    st.error("No medicines have been confirmed. Confirm at least one correctly identified medicine before analysis.")
                    st.stop()
                with st.spinner("Checking confirmed medicines…"):
                    s.state = stage2(state)
                s.done = True
                st.success("Analysis complete. Review tabs 3 and 4.")

with t3:
    if s.get("done"):
        st.subheader("Reconciliation findings")
        for finding in s.state.get("reconciliation", []):
            st.warning(f"**{finding['kind']}** · {finding['subject']}: {finding['note']}")
        st.subheader("Interaction screening")
        for finding in s.state.get("interactions", []):
            if finding["status"] == "match":
                record = finding["record"]
                st.error(f"**{finding['pair'][0].title()} + {finding['pair'][1].title()}** ({record['risk']}): {record['interaction']}\n\nMechanism: {record['mechanism']}  \nReference management information: {record['management']}  \nSource: {record['source']}")
            else:
                st.caption(f"{finding['pair'][0]} + {finding['pair'][1]}: {finding['message']}")
    else:
        st.info("Verify the medicines first, then run the analysis.")

with t4:
    if s.get("done"):
        st.markdown(s.state["report"])
        st.download_button("Download report (.md)", s.state["report"], "medication_safety_report.md")
    else:
        st.info("No report yet.")
