import streamlit as st
import pandas as pd
import os
from datetime import datetime
import requests
from PIL import Image
import google.generativeai as genai
import json
import re
from streamlit_option_menu import option_menu

st.set_page_config(page_title="CKD Early Detection (Isan & AI)", layout="wide")

# ===== Sidebar and Menu =====
with st.sidebar:
    st.title("🩺 CKD AI Isan")
    selected = option_menu(
        menu_title="เมนูหลัก",
        options=["คัดกรองใหม่", "ประวัติ/ติดตามผล", "สถิติภาพรวม"],
        icons=["plus-circle", "clock-history", "graph-up"],
        menu_icon="cast", default_index=0,
    )
    st.markdown("---")
    st.warning("⚠️ **Disclaimer:** ระบบคัดกรองเบื้องต้นเท่านั้น ไม่ใช่การวินิจฉัยโดยแพทย์")

# Configure AI model (Gemini)
# Configure AI model (Gemini)
# ดึง API Key จากความลับของ Streamlit แทนการฝังในโค้ด
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
except KeyError:
    st.error("🚨 ไม่พบ API Key! กรุณาตรวจสอบไฟล์ .streamlit/secrets.toml (สำหรับรันในเครื่อง) หรือตั้งค่า Secrets ใน Streamlit Cloud")
    st.stop()
model = genai.GenerativeModel('gemini-1.5-flash')

# ===== Main Content Based on Menu Selection =====
if selected == "คัดกรองใหม่":
    st.title("🌾 ระบบคัดกรองโรคไตเชิงรุกด้วย AI สำหรับเกษตรกรในจังหวัดสกลนคร")

    # 🔐 PDPA Notice
    with st.container():
        st.markdown("### 🔐 การคุ้มครองข้อมูลส่วนบุคคล (PDPA Notice)")
        st.write("ข้อมูลที่บันทึกจะถูกนำไปใช้เพื่อการวิเคราะห์ทางสถิติและพัฒนาระบบคัดกรองโรคไตเชิงรุกในพื้นที่เท่านั้น ข้อมูลจะถูกเก็บรักษาเป็นความลับตามมาตรฐาน")
        st.warning("⚠️ **ข้อจำกัดความรับผิดชอบ (Disclaimer):** ระบบนี้เป็นเพียงเครื่องมือคัดกรองความเสี่ยงเบื้องต้นด้วยอาสาสมัครและ AI เท่านั้น **ไม่ใช่การวินิจฉัยทางการแพทย์** ผลลัพธ์ที่ได้ไม่สามารถนำไปใช้ยืนยันการเป็นโรคไตได้ 100% ผู้ใช้งานควรปรึกษาแพทย์หรือบุคลากรสาธารณสุขเพื่อทำการตรวจมาตรฐาน (เช่น เจาะเลือดดูค่า eGFR) อีกครั้ง")
        consent = st.checkbox("ข้าพเจ้ายินยอมให้ระบบบันทึกข้อมูลและภาพถ่ายแผ่นตรวจปัสสาวะเพื่อใช้ในการคัดกรอง")
    if not consent:
        st.info("👈 กรุณาอ่านรายละเอียดและทำเครื่องหมายถูกในช่อง 'ยินยอม' เพื่อเริ่มต้นการใช้งาน")
        st.stop()

    st.markdown("ผสานการอ่านแผ่นปัสสาวะ 3 ค่า ด้วย AI เข้ากับการประเมินพฤติกรรมสุขภาพเชิงลึก")

    # 1. ข้อมูลทั่วไปของผู้รับการตรวจ
    with st.expander("📋 1. ข้อมูลทั่วไปของผู้รับการตรวจ", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            patient_id = st.text_input("📱 เบอร์โทรศัพท์ (สำคัญเพื่อใช้ติดตามผล)")
            name = st.text_input("ชื่อ-นามสกุล (ถ้าต้องการเก็บ)")
            age = st.number_input("อายุ (ปี)", min_value=1, max_value=120, value=45)
        with col2:
            gender = st.selectbox("เพศ", ["ชาย", "หญิง"])
        with col3:
            district = st.selectbox("📍 อำเภอที่ลงพื้นที่",
                                    ["อำเภอเมืองสกลนคร", "อำเภอกุสุมาลย์", "อำเภอพรรณานิคม", "อำเภอพังโคน", "อื่นๆ"])

    # 2. แบบประเมินปัจจัยเสี่ยงโรคไต
    st.markdown("### 🩺 2. แบบประเมินปัจจัยเสี่ยงโรคไต (Risk Factors)")
    st.info("💡 กรุณาสอบถามประวัติผู้รับการตรวจให้ครบถ้วน เพื่อการคำนวณคะแนนที่แม่นยำ")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**ประวัติโรคประจำตัว:**")
        has_diabetes = st.checkbox("🩸 โรคเบาหวาน (Diabetes)")
        has_hypertension = st.checkbox("💓 โรคความดันโลหิตสูง (Hypertension)")
        has_gout = st.checkbox("🦴 โรคเกาต์ / กรดยูริกสูง (Gout)")
        family_ckd = st.checkbox("👨‍👩‍👧 มีประวัติคนในครอบครัวเป็นโรคไต")
    with col2:
        st.markdown("**พฤติกรรมการใช้ยา:**")
        nsaids_usage = st.radio("💊 การใช้ยาแก้ปวด (NSAIDs) / ยาชุด / ยาลูกกลอน:",
                                ["ไม่ค่อยกิน", "กินเป็นประจำ"])
        st.markdown("**พฤติกรรมสุขภาพ:**")
        smoke_alcohol = st.checkbox("🚬 สูบบุหรี่ หรือ ดื่มสุราเป็นประจำ")
    with col3:
        st.markdown("**บริบทเฉพาะถิ่น (วิถีชีวิตชาวเกษตรกร):**")
        has_stones = st.checkbox("🪨 มีประวัติโรคนิ่วในไต / ปัสสาวะขัดบ่อยๆ")
        high_sodium = st.checkbox("🧂 ทานอาหารรสเค็มจัด / ปลาร้า / ผงชูรสปริมาณมาก")
        chemical_exposure = st.checkbox("🧪 สัมผัสสารเคมีทางการเกษตร (ยาฆ่าหญ้า/แมลง) เป็นประจำ")

    st.markdown("---")
    # 3. กล้องถ่ายภาพและ AI วิเคราะห์
    st.header("📷 3. ถ่ายภาพแผ่นทดสอบ (Dipstick)")
    st.info("💡 ถ่ายให้เห็นแถบสี 3 ค่าบนแผ่นทดสอบ (โปรตีน, เลือด, น้ำตาล) ชัดเจน AI จะทำการวิเคราะห์อัตโนมัติ")
    img_file = st.camera_input("📸 ถ่ายภาพแผ่นตรวจ (ไม่ต้องเล็งกรอบ)")

    if "ai_data" not in st.session_state:
        st.session_state.ai_data = None

    if img_file is not None:
        st.markdown("---")
        st.header("🧠 4. ผลการวิเคราะห์สีแผ่นปัสสาวะโดย AI")
        col_img, col_ai = st.columns([1, 2])
        with col_img:
            image = Image.open(img_file)
            st.image(image, caption="ภาพที่รับเข้าสู่ระบบ AI", use_container_width=True)
        with col_ai:
            if st.session_state.ai_data is None:
                with st.spinner("🤖 AI กำลังประมวลผล..."):
                    try:
                        prompt = """
คุณคือผู้เชี่ยวชาญด้านเทคนิคการแพทย์ ตรวจสอบภาพแผ่นทดสอบปัสสาวะ (Dipstick) 3 ค่า
ให้อ่านค่า 3 อย่างเรียงจากบนลงล่าง: Protein, Blood, Glucose
ส่งคำตอบเป็น JSON รูปแบบนี้เท่านั้น:
{
    "Protein": "Negative หรือ Trace หรือ +1 ถึง +4",
    "Blood": "Negative หรือ Trace หรือ +1 ถึง +4",
    "Glucose": "Negative หรือ Trace หรือ +1 ถึง +4",
    "Confidence": "ความมั่นใจ 1-100",
    "Note": "ข้อสังเกตสั้นๆ"
}
"""
                        response = model.generate_content([prompt, image])
                        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                        st.session_state.ai_data = json.loads(json_match.group(0))
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ AI ไม่สามารถอ่านค่าได้ กรุณาถ่ายภาพใหม่อีกครั้ง: {e}")
                        st.stop()
            if st.session_state.ai_data:
                ai_data = st.session_state.ai_data
                st.success("✨ AI วิเคราะห์ภาพสำเร็จแล้ว!")
                m1, m2, m3 = st.columns(3)
                m1.metric("🦠 Protein (โปรตีน)", ai_data.get("Protein", "N/A"))
                m2.metric("🩸 Blood (เลือดปน)", ai_data.get("Blood", "N/A"))
                m3.metric("🍬 Glucose (น้ำตาล)", ai_data.get("Glucose", "N/A"))
                st.caption(f"**ความมั่นใจของ AI:** {ai_data.get('Confidence', 'N/A')}% | **บันทึก AI:** {ai_data.get('Note', '')}")

        # 🚨 5. คำนวณความเสี่ยง (Advanced Risk Scoring)
        if st.session_state.ai_data:
            st.markdown("---")
            st.header("🚨 5. สรุปผลการประเมินความเสี่ยงโรคไต (CKD Risk Score)")
            risk_score = 0
            # 1. คะแนนจากประวัติสุขภาพพื้นฐาน
            if age >= 60: risk_score += 1
            if has_diabetes: risk_score += 2
            if has_hypertension: risk_score += 2
            if has_gout: risk_score += 1
            if family_ckd: risk_score += 2
            if smoke_alcohol: risk_score += 1
            # 2. คะแนนจากวิถีชีวิตและการใช้ยา
            if nsaids_usage == "กินเป็นประจำ": risk_score += 2
            if has_stones: risk_score += 2
            if high_sodium: risk_score += 1
            if chemical_exposure: risk_score += 1
            # 3. คะแนนจากผล AI ตรวจปัสสาวะ
            protein_val = ai_data.get("Protein", "Negative")
            if "Trace" in protein_val or "+1" in protein_val: risk_score += 2
            elif any(x in protein_val for x in ["+2", "+3", "+4"]): risk_score += 4
            blood_val = ai_data.get("Blood", "Negative")
            if any(x in blood_val for x in ["Trace", "+1", "+2", "+3", "+4"]): risk_score += 2
            glucose_val = ai_data.get("Glucose", "Negative")
            if any(x in glucose_val for x in ["Trace", "+1", "+2", "+3", "+4"]): risk_score += 1
            # ประเมินเกณฑ์
            if risk_score >= 8:
                result_text, status_color = "ความเสี่ยงสูงมาก (High Risk)", "🔴"
                advice = "🚨 **ต้องส่งต่อแพทย์ด่วน:** ควรได้รับการเจาะเลือดตรวจค่า eGFR และอัลตราซาวด์ไตโดยเร็วที่สุด"
            elif 4 <= risk_score <= 7:
                result_text, status_color = "ความเสี่ยงปานกลาง (Moderate Risk)", "🟡"
                advice = "⚠️ **ต้องปรับพฤติกรรม:** งดเค็ม งดยาชุด ดื่มน้ำให้เพียงพอ และนัดมาตรวจปัสสาวะซ้ำใน 2-4 สัปดาห์"
            else:
                result_text, status_color = "ความเสี่ยงต่ำ / ปกติ (Low Risk)", "🟢"
                advice = "✅ **สุขภาพไตยังดี:** ให้รักษาพฤติกรรมสุขภาพ ดื่มน้ำสะอาดให้เพียงพอเวลาทำเกษตร"
            with st.container():
                r1, r2 = st.columns([1, 2])
                with r1:
                    st.metric(label="Total Risk Score", value=f"{risk_score} คะแนน")
                with r2:
                    st.markdown(f"### {status_color} {result_text}")
                    st.write(advice)
            if risk_score >= 4:
                st.markdown("---")
                st.subheader(f"🏥 สถานพยาบาลแนะนำใน {district}")
                hospitals = {
                    "อำเภอเมืองสกลนคร": {"name": "โรงพยาบาลสกลนคร", "tel": "042-711-037", "map": "https://maps.app.goo.gl/8MiWG8R4L1EPcn9G6"},
                    "อำเภอกุสุมาลย์": {"name": "โรงพยาบาลกุสุมาลย์", "tel": "042-769-023", "map": "https://maps.app.goo.gl/GbgQKZvM6Vc1ZdR67"},
                    "อำเภอพรรณานิคม": {"name": "โรงพยาบาลพระอาจารย์ฝั้น อาจาโร", "tel": "042-741-111", "map": "https://maps.app.goo.gl/C9otZ5inMsWnmC6A9"},
                    "อำเภอพังโคน": {"name": "โรงพยาบาลพังโคน", "tel": "042-771-222", "map": "https://maps.app.goo.gl/JAmGRM7HPcnT1SVs8"},
                    "อื่นๆ": {"name": "สถานพยาบาลใกล้บ้านท่าน", "tel": "1669"}
                }
                hospital_info = hospitals.get(district, hospitals["อื่นๆ"])
                col_h1, col_h2 = st.columns(2)
                with col_h1:
                    st.info(f"**ชื่อ:** {hospital_info['name']}  **📞 เบอร์โทร:** {hospital_info['tel']}")
                with col_h2:
                    st.link_button(f"📍 นำทางไป {hospital_info['name']}", hospital_info["map"], use_container_width=True)
                    st.caption("หมายเหตุ: ข้อมูลนี้เป็นการประเมินความเสี่ยงเบื้องต้น โปรดนำผลนี้ปรึกษาเจ้าหน้าที่สาธารณสุขในพื้นที่ของท่าน")
            st.markdown("---")
            # 💾 6. บันทึกข้อมูลเข้าระบบ
            st.header("💾 6. บันทึกข้อมูลเข้าระบบ")
            if "is_submitted" not in st.session_state:
                st.session_state.is_submitted = False
            if st.button("📥 ยืนยันผลและบันทึกข้อมูล", type="primary", use_container_width=True, disabled=st.session_state.is_submitted):
                with st.spinner("กำลังบันทึกข้อมูลและเก็บภาพเข้าเซิร์ฟเวอร์..."):
                    try:
                        if not os.path.exists("captured_images"):
                            os.makedirs("captured_images")
                        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                        image_filename = f"ckd_{timestamp_str}.jpg"
                        image_path = os.path.join("captured_images", image_filename)
                        image.save(image_path)
                        new_data = pd.DataFrame([{
                            "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "Patient_ID": str(patient_id),
                            "Name": name,
                            "District": district,
                            "Age": age,
                            "Gender": gender,
                            "DM": "Yes" if has_diabetes else "No",
                            "HT": "Yes" if has_hypertension else "No",
                            "Gout": "Yes" if has_gout else "No",
                            "Family_CKD": "Yes" if family_ckd else "No",
                            "NSAIDs": nsaids_usage,
                            "Stones": "Yes" if has_stones else "No",
                            "High_Sodium": "Yes" if high_sodium else "No",
                            "Chemicals": "Yes" if chemical_exposure else "No",
                            "AI_Protein": protein_val,
                            "AI_Blood": blood_val,
                            "AI_Glucose": glucose_val,
                            "Total_Score": risk_score,
                            "Result": result_text,
                            "Image_File": image_filename
                        }])
                        file_name = "ckd_database.csv"
                        if os.path.exists(file_name):
                            new_data.to_csv(file_name, mode='a', header=False, index=False)
                        else:
                            new_data.to_csv(file_name, index=False)
                        # ส่งข้อมูลไป Google Forms
                        FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdmHo3tH30h7iOe0ckfoktY6aPk_R7eTAbunYy0dbqXNOWPoQ/formResponse"
                        form_data = {
                            "entry.226071067": str(district),
                            "entry.1224620038": str(age),
                            "entry.1030234450": str(gender),
                            "entry.853278913": "เป็น" if has_diabetes else "ไม่เป็น",
                            "entry.1930442439": "เป็น" if has_hypertension else "ไม่เป็น",
                            "entry.1061500560": "เป็น" if has_gout else "ไม่เป็น",
                            "entry.2005371488": "มี" if family_ckd else "ไม่มี",
                            "entry.853069744": str(nsaids_usage),
                            "entry.643930526": f"PRO:{protein_val}, BLD:{blood_val}, GLU:{glucose_val}",
                            "entry.19531897": str(risk_score),
                            "entry.1594709429": str(result_text),
                            "entry.1993082703": "เป็น" if has_stones else "ไม่เป็น",
                            "entry.1517620614": "เป็น" if high_sodium else "ไม่เป็น",
                            "entry.1278780738": "เป็น" if chemical_exposure else "ไม่เป็น"
                        }
                        response = requests.post(FORM_URL, data=form_data)
                        if response.status_code == 200:
                            st.session_state.is_submitted = True
                            st.success("✅ บันทึกข้อมูลและรูปภาพสำเร็จ!")
                        else:
                            st.error(f"❌ Google Forms แจ้งเตือน: {response.status_code}")
                    except Exception as e:
                        st.error(f"❌ ระบบขัดข้อง: {e}")
            if st.session_state.is_submitted:
                if st.button("🔄 เริ่มตรวจผู้รับบริการคนต่อไป", use_container_width=True):
                    st.session_state.ai_data = None
                    st.session_state.is_submitted = False
                    st.rerun()

elif selected == "ประวัติ/ติดตามผล":
    st.header("🕒 ติดตามผลและวิเคราะห์แนวโน้มสุขภาพ")
    search_id = st.text_input("🔍 ค้นหาด้วยเบอร์โทรศัพท์", placeholder="เช่น 0812345678")
    if search_id:
        if os.path.exists("ckd_database.csv"):
            df = pd.read_csv("ckd_database.csv")
            patient_data = df[df['Patient_ID'].astype(str) == search_id]
            patient_data = patient_data.sort_values(by='Date')
            if not patient_data.empty:
                latest = patient_data.iloc[-1]
                prev_data = patient_data.iloc[-2] if len(patient_data) > 1 else None
                col1, col2 = st.columns(2)
                with col1:
                    if prev_data is not None:
                        diff = int(latest['Total_Score']) - int(prev_data['Total_Score'])
                        st.metric("คะแนนล่าสุด", f"{latest['Total_Score']} แต้ม", delta=f"{diff}", delta_color="inverse")
                    else:
                        st.metric("คะแนนครั้งแรก", f"{latest['Total_Score']} แต้ม")
                with col2:
                    st.write(f"วันที่บันทึกล่าสุด: {latest['Date']}")
                st.line_chart(patient_data.set_index('Date')['Total_Score'])
                if st.button("🪄 ให้ AI วิเคราะห์ความเปลี่ยนแปลง"):
                    history_text = patient_data[['Date','Total_Score','Result']].to_string(index=False)
                    resp = model.generate_content(f"วิเคราะห์แนวโน้มสุขภาพจากข้อมูลนี้: {history_text}")
                    st.info(resp.text)
            else:
                st.warning("❌ ไม่พบข้อมูลสำหรับเบอร์โทรศัพท์นี้")
        else:
            st.info("ℹ️ ยังไม่มีข้อมูลบันทึก")

elif selected == "สถิติภาพรวม":
    st.subheader("📊 Dashboard: สถิติผู้เข้ารับการคัดกรอง")
    file_name = "ckd_database.csv"
    if os.path.exists(file_name):
        df = pd.read_csv(file_name)
        if not df.empty:
            st.subheader("📋 ข้อมูลล่าสุด (5 รายการ)")
            st.dataframe(df.tail(5), use_container_width=True)
            st.divider()
            c_chart1, c_chart2 = st.columns(2)
            with c_chart1:
                st.subheader("📈 ระดับความเสี่ยงในพื้นที่")
                if "Result" in df.columns:
                    risk_counts = df["Result"].value_counts()
                    st.bar_chart(risk_counts)
                else:
                    st.info("ยังไม่มีข้อมูล Result")
            with c_chart2:
                st.subheader("⚠️ ปัจจัยเสี่ยงที่ตรวจพบ")
                risk_summary = {
                    "เบาหวาน": (df["DM"] == "Yes").sum() if "DM" in df.columns else 0,
                    "ความดัน": (df["HT"] == "Yes").sum() if "HT" in df.columns else 0,
                    "กินเค็ม": (df["High_Sodium"] == "Yes").sum() if "High_Sodium" in df.columns else 0,
                    "นิ่ว": (df["Stones"] == "Yes").sum() if "Stones" in df.columns else 0,
                    "สารเคมี": (df["Chemicals"] == "Yes").sum() if "Chemicals" in df.columns else 0
                }
                st.bar_chart(pd.Series(risk_summary))
            st.subheader("📍 จำนวนผู้เข้ารับการตรวจแยกตามอำเภอ")
            if "District" in df.columns:
                district_counts = df["District"].value_counts()
                st.bar_chart(district_counts)
        else:
            st.warning("⚠️ พบไฟล์ฐานข้อมูลแต่ยังไม่มีรายการบันทึก")
    else:
        st.info("ℹ️ ยังไม่มีข้อมูลในระบบ")
