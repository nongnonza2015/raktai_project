import streamlit as st
import pandas as pd
import os
from datetime import datetime
import requests
from PIL import Image
import google.generativeai as genai
import json
AIzaSyDvsHoM1Kvg4O8IP7uXZxfXO34DFTnRIi8 = "import streamlit as st
import pandas as pd
import os
from datetime import datetime
import requests
from PIL import Image
import google.generativeai as genai
import json

# ==========================================
# 🔑 การตั้งค่า Gemini API (ใส่ API Key ของคุณตรงนี้)
# ==========================================
GEMINI_API_KEY = "AIzaSyDvsHoM1Kvg4O8IP7uXZxfXO34DFTnRIi8" 
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# ==========================================
# ส่วนที่ 1: การตั้งค่าหน้าเว็บ & ข้อมูลผู้ป่วย
# ==========================================
st.set_page_config(page_title="CKD Early Detection (AI Dipstick)", layout="centered")

st.title("🌾 ระบบคัดกรองโรคไตเบื้องต้นด้วย Gemini AI")
st.markdown("วิเคราะห์แผ่นปัสสาวะ 3 ค่า (โปรตีน, น้ำตาล, เลือด) อัตโนมัติ")

st.header("📋 1. ข้อมูลผู้รับการตรวจ (General Information)")
st.info("ข้อมูลเหล่านี้จะถูกนำไปคำนวณร่วมกับผลปัสสาวะ เพื่อประเมินความเสี่ยงที่แม่นยำขึ้น")

col1, col2 = st.columns(2)
with col1:
    age = st.number_input("อายุ (ปี)", min_value=1, max_value=120, value=45)
    gender = st.selectbox("เพศ", ["ชาย", "หญิง"])

st.markdown("---")
st.subheader("📍 พื้นที่ปฏิบัติงาน (สำหรับ อสม. / รพ.สต.)")
district = st.selectbox("เลือกอำเภอที่ลงพื้นที่คัดกรอง", 
                        ["อำเภอเมืองสกลนคร", "อำเภอกุสุมาลย์", "อำเภอพรรณานิคม", "อำเภอพังโคน", "อื่นๆ"])

st.markdown("**🩺 ข้อมูลสุขภาพเพิ่มเติม (ปัจจัยเสี่ยง)**")
col3, col4 = st.columns(2)
with col3:
    has_diabetes = st.checkbox("โรคเบาหวาน")              
    has_hypertension = st.checkbox("โรคความดันโลหิตสูง")
with col4:
    nsaids_usage = st.radio("ความถี่ในการกินยาแก้ปวด (NSAIDs)", 
                            ["ไม่เคยกิน / กินนานๆ ครั้ง", "กินประจำ (มากกว่า 2 ครั้ง/สัปดาห์)"])

st.markdown("---")

# ==========================================
# ส่วนที่ 2: กล้องถ่ายภาพ
# ==========================================
st.header("📷 2. ถ่ายภาพแผ่นทดสอบ (Dipstick)")
st.info("💡 นำแผ่นตรวจปัสสาวะมาวางเทียบกับข้างขวดสี แล้วกดถ่ายภาพให้เห็นทั้งแผ่นและแถบสีอ้างอิงชัดเจน")

img_file = st.camera_input("📸 ส่องแผ่นตรวจเทียบกับขวดสีให้ชัดเจนแล้วกดถ่ายภาพ")

# ==========================================
# ส่วนที่ 3: ให้ Gemini AI วิเคราะห์ภาพ
# ==========================================
if img_file is not None:
    st.markdown("---")
    st.header("🧠 3. ผลการวิเคราะห์โดย AI")
    
    image = Image.open(img_file)
    st.image(image, caption="ภาพที่ AI กำลังวิเคราะห์", width=300)
    
    # ดึงค่า AI จาก Session State (ถ้ายังไม่มีให้เริ่มคำนวณ)
    if "ai_data" not in st.session_state:
        st.session_state.ai_data = None

    if st.session_state.ai_data is None:
        with st.spinner("🤖 AI กำลังประมวลผลสีและอ่านค่าทั้ง 3 ชนิด..."):
            try:
                # Prompt สั่งงาน Gemini ให้ตอบกลับเป็น JSON
                prompt = """
                คุณคือผู้เชี่ยวชาญด้านเทคนิคการแพทย์ กรุณาตรวจสอบภาพแผ่นทดสอบปัสสาวะ (Dipstick) นี้เทียบกับตารางสีข้างขวด
                ให้อ่านค่า 3 อย่าง: Protein, Glucose, Blood
                ส่งคำตอบเป็น JSON รูปแบบนี้เท่านั้น ห้ามมีคำอธิบายอื่น:
                {
                    "Protein": "ระบุค่า (เช่น Negative, Trace, +1, +2, +3, +4)",
                    "Glucose": "ระบุค่า (เช่น Negative, Trace, +1, +2, +3, +4)",
                    "Blood": "ระบุค่า (เช่น Negative, Trace, +1, +2, +3, +4)",
                    "Confidence": "ความมั่นใจ 1-100",
                    "Note": "ข้อสังเกตเพิ่มเติม"
                }
                """
                response = model.generate_content([prompt, image])
                
                # ทำความสะอาดข้อความเพื่อดึงแค่ JSON
                result_text = response.text.strip()
                if result_text.startswith("```json"):
                    result_text = result_text[7:-3]
                elif result_text.startswith("```"):
                    result_text = result_text[3:-3]
                    
                st.session_state.ai_data = json.loads(result_text)
                st.rerun() # สั่งรันหน้าเว็บใหม่เพื่อให้กล่องคะแนนโชว์
            except Exception as e:
                st.error(f"❌ เกิดข้อผิดพลาดในการวิเคราะห์: {e}")
                st.stop()

    # ถ้ามีข้อมูล AI แล้ว ให้นำมาแสดงผล
    if st.session_state.ai_data:
        ai_data = st.session_state.ai_data
        st.success("✨ AI วิเคราะห์ภาพสำเร็จแล้ว!")
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("🦠 Protein (โปรตีน)", ai_data.get("Protein", "N/A"))
        col_b.metric("🍬 Glucose (น้ำตาล)", ai_data.get("Glucose", "N/A"))
        col_c.metric("🩸 Blood (เลือด)", ai_data.get("Blood", "N/A"))
        
        st.caption(f"**ความมั่นใจของ AI:** {ai_data.get('Confidence', 'N/A')}% | **หมายเหตุ AI:** {ai_data.get('Note', '')}")

        # ==========================================
        # ส่วนที่ 4: คำนวณความเสี่ยง (Risk Scoring)
        # ==========================================
        st.markdown("---")
        st.header("🚨 4. สรุปผลการประเมินความเสี่ยง")
        
        # ลอจิกการให้คะแนนแบบเดิม + ค่าอื่นๆ จาก AI
        risk_score = 0
        if age >= 60: risk_score += 1
        if has_diabetes: risk_score += 2
        if has_hypertension: risk_score += 1
        if nsaids_usage == "กินประจำ (มากกว่า 2 ครั้ง/สัปดาห์)": risk_score += 2

        protein_val = ai_data.get("Protein", "Negative")
        if "Trace" in protein_val or "+1" in protein_val: risk_score += 2
        elif any(x in protein_val for x in ["+2", "+3", "+4"]): risk_score += 4
            
        glucose_val = ai_data.get("Glucose", "Negative")
        if any(x in glucose_val for x in ["+1", "+2", "+3", "+4"]): risk_score += 1
            
        blood_val = ai_data.get("Blood", "Negative")
        if any(x in blood_val for x in ["+1", "+2", "+3", "+4"]): risk_score += 1

        # ประเมินสถานะ
        if risk_score >= 6:
            result_text, status_color = "ความเสี่ยงสูงมาก", "🔴"
            st.error(f"### {status_color} {result_text} (คะแนนรวม: {risk_score})")
            advice = "🚨 ควรส่งต่อพบแพทย์เพื่อเจาะเลือดตรวจค่าไต (eGFR) และน้ำตาลในเลือดทันที"
        elif 4 <= risk_score <= 5:
            result_text, status_color = "ความเสี่ยงปานกลาง", "🟡"
            st.warning(f"### {status_color} {result_text} (คะแนนรวม: {risk_score})")
            advice = "⚠️ ควรปรับพฤติกรรมการกิน ลดเค็ม เลิกยาแก้ปวด และนัดตรวจปัสสาวะซ้ำใน 2 สัปดาห์"
        else:
            result_text, status_color = "ความเสี่ยงต่ำ / ปกติ", "🟢"
            st.success(f"### {status_color} {result_text} (คะแนนรวม: {risk_score})")
            advice = "✅ รักษาพฤติกรรมสุขภาพที่ดี ดื่มน้ำให้เพียงพอ และตรวจสุขภาพประจำปี"

        st.info(f"**📝 คำแนะนำ:** {advice}")

        # ==========================================
        # ส่วนที่ 5: บันทึกข้อมูล
        # ==========================================
        st.markdown("---")
        st.header("💾 5. บันทึกข้อมูลลงฐานข้อมูล")

        # ตกแต่งปุ่มด้วย CSS (สีเขียว)
        st.markdown("""
        <style>
        button[kind="primary"] {
            background-color: #059669 !important; border-color: #059669 !important;
            color: white !important; font-weight: bold !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        button[kind="primary"]:hover { background-color: #047857 !important; border-color: #047857 !important; }
        </style>
        """, unsafe_allow_html=True)

        # ล็อคปุ่มกันกดรัว
        if "is_submitted" not in st.session_state:
            st.session_state.is_submitted = False

        if st.button("📥 ยืนยันและบันทึกผลการคัดกรองเคสนี้", type="primary", use_container_width=True, disabled=st.session_state.is_submitted):
            with st.spinner("กำลังบันทึกข้อมูล..."):
                try:
                    # 1. บันทึกลง Local CSV
                    new_data = pd.DataFrame([{
                        "วันที่ตรวจ": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "อำเภอ": district, "อายุ": age, "เพศ": gender,
                        "เบาหวาน": "เป็น" if has_diabetes else "ไม่เป็น",
                        "ความดัน": "เป็น" if has_hypertension else "ไม่เป็น",
                        "โปรตีน": protein_val, "น้ำตาล": glucose_val, "เลือด": blood_val,
                        "คะแนนความเสี่ยง": risk_score, "ผลการประเมิน": result_text
                    }])
                    
                    file_name = "ckd_database.csv"
                    if os.path.exists(file_name):
                        new_data.to_csv(file_name, mode='a', header=False, index=False)
                    else:
                        new_data.to_csv(file_name, index=False)

                    # 2. ส่งไป Google Forms (ปรับใช้ Field เดิมของคุณ แต่เติมค่าเข้าไปในฟิลด์ Note หรือดัดแปลงได้ตามสะดวก)
                    # ตรงนี้ผมใช้ฟิลด์เดิมที่คุณให้มา เพื่อไม่ให้ Form พังครับ
                    FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdmHo3tH30h7iOe0ckfoktY6aPk_R7eTAbunYy0dbqXNOWPoQ/formResponse"
                    form_data = {
                        "entry.226071067": str(district), "entry.1224620038": str(age), "entry.1030234450": str(gender),
                        "entry.853278913": "เป็น" if has_diabetes else "ไม่เป็น", "entry.1930442439": "เป็น" if has_hypertension else "ไม่เป็น",
                        "entry.853069744": str(nsaids_usage), "entry.643930526": str(protein_val), # ใช้ช่องนี้เก็บโปรตีนไปก่อน
                        "entry.19531897": str(risk_score), "entry.1594709429": str(result_text)
                    }
                    response = requests.post(FORM_URL, data=form_data)
                    
                    if response.status_code == 200:
                        st.session_state.is_submitted = True # ล็อคปุ่ม
                        st.success("✅ บันทึกข้อมูลสำเร็จ!")
                        st.toast("บันทึกข้อมูลเข้าสู่ระบบเรียบร้อย", icon="✅")
                    else:
                        st.error(f"❌ Google Forms ปฏิเสธข้อมูล (Error {response.status_code})")
                        
                except Exception as e:
                    st.error(f"❌ ไม่สามารถส่งข้อมูลได้: {e}")

        # ปุ่มเริ่มตรวจคนใหม่
        if st.session_state.is_submitted:
            if st.button("🔄 เริ่มตรวจคนต่อไป", use_container_width=True):
                # เคลียร์ค่าทั้งหมด
                st.session_state.ai_data = None
                st.session_state.is_submitted = False
                st.rerun()

# ==========================================
# ส่วนเสริม: Dashboard
# ==========================================
st.markdown("---")
with st.expander("📊 คลิกที่นี่เพื่อดู Dashboard สถิติเฝ้าระวังโรคไต", expanded=False):
    if os.path.exists("ckd_database.csv"):
        df = pd.read_csv("ckd_database.csv")
        st.dataframe(df, use_container_width=True)
            
        st.markdown("---")
        st.subheader("📈 แผนภูมิผู้ที่มีความเสี่ยง (แบ่งตามอำเภอ)")
        risk_df = df[df["ผลการประเมิน"].isin(["ความเสี่ยงสูงมาก", "ความเสี่ยงปานกลาง"])]
        if not risk_df.empty:
            st.bar_chart(risk_df["อำเภอ"].value_counts())
        else:
            st.info("ยังไม่มีผู้ป่วยที่มีความเสี่ยงในระบบ")
            
        st.markdown("---")
        if st.button("🗑️ ล้างข้อมูลทดสอบทั้งหมด", type="secondary"):
            os.remove("ckd_database.csv")
            st.session_state.ai_data = None
            st.session_state.is_submitted = False
            st.rerun()
    else:
        st.info("ยังไม่มีข้อมูลในระบบ กราฟจะแสดงผลเมื่อมีการบันทึกข้อมูลแล้วครับ")" # <<<< เปลี่ยนตรงนี้
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# ==========================================
# ส่วนที่ 1: การตั้งค่าหน้าเว็บ & ข้อมูลผู้ป่วย
# ==========================================
st.set_page_config(page_title="CKD Early Detection (AI Dipstick)", layout="centered")

st.title("🌾 ระบบคัดกรองโรคไตเบื้องต้นด้วย Gemini AI")
st.markdown("วิเคราะห์แผ่นปัสสาวะ 3 ค่า (โปรตีน, น้ำตาล, เลือด) อัตโนมัติ")

st.header("📋 1. ข้อมูลผู้รับการตรวจ (General Information)")
st.info("ข้อมูลเหล่านี้จะถูกนำไปคำนวณร่วมกับผลปัสสาวะ เพื่อประเมินความเสี่ยงที่แม่นยำขึ้น")

col1, col2 = st.columns(2)
with col1:
    age = st.number_input("อายุ (ปี)", min_value=1, max_value=120, value=45)
    gender = st.selectbox("เพศ", ["ชาย", "หญิง"])

st.markdown("---")
st.subheader("📍 พื้นที่ปฏิบัติงาน (สำหรับ อสม. / รพ.สต.)")
district = st.selectbox("เลือกอำเภอที่ลงพื้นที่คัดกรอง", 
                        ["อำเภอเมืองสกลนคร", "อำเภอกุสุมาลย์", "อำเภอพรรณานิคม", "อำเภอพังโคน", "อื่นๆ"])

st.markdown("**🩺 ข้อมูลสุขภาพเพิ่มเติม (ปัจจัยเสี่ยง)**")
col3, col4 = st.columns(2)
with col3:
    has_diabetes = st.checkbox("โรคเบาหวาน")              
    has_hypertension = st.checkbox("โรคความดันโลหิตสูง")
with col4:
    nsaids_usage = st.radio("ความถี่ในการกินยาแก้ปวด (NSAIDs)", 
                            ["ไม่เคยกิน / กินนานๆ ครั้ง", "กินประจำ (มากกว่า 2 ครั้ง/สัปดาห์)"])

st.markdown("---")

# ==========================================
# ส่วนที่ 2: กล้องถ่ายภาพ
# ==========================================
st.header("📷 2. ถ่ายภาพแผ่นทดสอบ (Dipstick)")
st.info("💡 นำแผ่นตรวจปัสสาวะมาวางเทียบกับข้างขวดสี แล้วกดถ่ายภาพให้เห็นทั้งแผ่นและแถบสีอ้างอิงชัดเจน")

img_file = st.camera_input("📸 ส่องแผ่นตรวจเทียบกับขวดสีให้ชัดเจนแล้วกดถ่ายภาพ")

# ==========================================
# ส่วนที่ 3: ให้ Gemini AI วิเคราะห์ภาพ
# ==========================================
if img_file is not None:
    st.markdown("---")
    st.header("🧠 3. ผลการวิเคราะห์โดย AI")
    
    image = Image.open(img_file)
    st.image(image, caption="ภาพที่ AI กำลังวิเคราะห์", width=300)
    
    # ดึงค่า AI จาก Session State (ถ้ายังไม่มีให้เริ่มคำนวณ)
    if "ai_data" not in st.session_state:
        st.session_state.ai_data = None

    if st.session_state.ai_data is None:
        with st.spinner("🤖 AI กำลังประมวลผลสีและอ่านค่าทั้ง 3 ชนิด..."):
            try:
                # Prompt สั่งงาน Gemini ให้ตอบกลับเป็น JSON
                prompt = """
                คุณคือผู้เชี่ยวชาญด้านเทคนิคการแพทย์ กรุณาตรวจสอบภาพแผ่นทดสอบปัสสาวะ (Dipstick) นี้เทียบกับตารางสีข้างขวด
                ให้อ่านค่า 3 อย่าง: Protein, Glucose, Blood
                ส่งคำตอบเป็น JSON รูปแบบนี้เท่านั้น ห้ามมีคำอธิบายอื่น:
                {
                    "Protein": "ระบุค่า (เช่น Negative, Trace, +1, +2, +3, +4)",
                    "Glucose": "ระบุค่า (เช่น Negative, Trace, +1, +2, +3, +4)",
                    "Blood": "ระบุค่า (เช่น Negative, Trace, +1, +2, +3, +4)",
                    "Confidence": "ความมั่นใจ 1-100",
                    "Note": "ข้อสังเกตเพิ่มเติม"
                }
                """
                response = model.generate_content([prompt, image])
                
                # ทำความสะอาดข้อความเพื่อดึงแค่ JSON
                result_text = response.text.strip()
                if result_text.startswith("```json"):
                    result_text = result_text[7:-3]
                elif result_text.startswith("```"):
                    result_text = result_text[3:-3]
                    
                st.session_state.ai_data = json.loads(result_text)
                st.rerun() # สั่งรันหน้าเว็บใหม่เพื่อให้กล่องคะแนนโชว์
            except Exception as e:
                st.error(f"❌ เกิดข้อผิดพลาดในการวิเคราะห์: {e}")
                st.stop()

    # ถ้ามีข้อมูล AI แล้ว ให้นำมาแสดงผล
    if st.session_state.ai_data:
        ai_data = st.session_state.ai_data
        st.success("✨ AI วิเคราะห์ภาพสำเร็จแล้ว!")
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("🦠 Protein (โปรตีน)", ai_data.get("Protein", "N/A"))
        col_b.metric("🍬 Glucose (น้ำตาล)", ai_data.get("Glucose", "N/A"))
        col_c.metric("🩸 Blood (เลือด)", ai_data.get("Blood", "N/A"))
        
        st.caption(f"**ความมั่นใจของ AI:** {ai_data.get('Confidence', 'N/A')}% | **หมายเหตุ AI:** {ai_data.get('Note', '')}")

        # ==========================================
        # ส่วนที่ 4: คำนวณความเสี่ยง (Risk Scoring)
        # ==========================================
        st.markdown("---")
        st.header("🚨 4. สรุปผลการประเมินความเสี่ยง")
        
        # ลอจิกการให้คะแนนแบบเดิม + ค่าอื่นๆ จาก AI
        risk_score = 0
        if age >= 60: risk_score += 1
        if has_diabetes: risk_score += 2
        if has_hypertension: risk_score += 1
        if nsaids_usage == "กินประจำ (มากกว่า 2 ครั้ง/สัปดาห์)": risk_score += 2

        protein_val = ai_data.get("Protein", "Negative")
        if "Trace" in protein_val or "+1" in protein_val: risk_score += 2
        elif any(x in protein_val for x in ["+2", "+3", "+4"]): risk_score += 4
            
        glucose_val = ai_data.get("Glucose", "Negative")
        if any(x in glucose_val for x in ["+1", "+2", "+3", "+4"]): risk_score += 1
            
        blood_val = ai_data.get("Blood", "Negative")
        if any(x in blood_val for x in ["+1", "+2", "+3", "+4"]): risk_score += 1

        # ประเมินสถานะ
        if risk_score >= 6:
            result_text, status_color = "ความเสี่ยงสูงมาก", "🔴"
            st.error(f"### {status_color} {result_text} (คะแนนรวม: {risk_score})")
            advice = "🚨 ควรส่งต่อพบแพทย์เพื่อเจาะเลือดตรวจค่าไต (eGFR) และน้ำตาลในเลือดทันที"
        elif 4 <= risk_score <= 5:
            result_text, status_color = "ความเสี่ยงปานกลาง", "🟡"
            st.warning(f"### {status_color} {result_text} (คะแนนรวม: {risk_score})")
            advice = "⚠️ ควรปรับพฤติกรรมการกิน ลดเค็ม เลิกยาแก้ปวด และนัดตรวจปัสสาวะซ้ำใน 2 สัปดาห์"
        else:
            result_text, status_color = "ความเสี่ยงต่ำ / ปกติ", "🟢"
            st.success(f"### {status_color} {result_text} (คะแนนรวม: {risk_score})")
            advice = "✅ รักษาพฤติกรรมสุขภาพที่ดี ดื่มน้ำให้เพียงพอ และตรวจสุขภาพประจำปี"

        st.info(f"**📝 คำแนะนำ:** {advice}")

        # ==========================================
        # ส่วนที่ 5: บันทึกข้อมูล
        # ==========================================
        st.markdown("---")
        st.header("💾 5. บันทึกข้อมูลลงฐานข้อมูล")

        # ตกแต่งปุ่มด้วย CSS (สีเขียว)
        st.markdown("""
        <style>
        button[kind="primary"] {
            background-color: #059669 !important; border-color: #059669 !important;
            color: white !important; font-weight: bold !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        button[kind="primary"]:hover { background-color: #047857 !important; border-color: #047857 !important; }
        </style>
        """, unsafe_allow_html=True)

        # ล็อคปุ่มกันกดรัว
        if "is_submitted" not in st.session_state:
            st.session_state.is_submitted = False

        if st.button("📥 ยืนยันและบันทึกผลการคัดกรองเคสนี้", type="primary", use_container_width=True, disabled=st.session_state.is_submitted):
            with st.spinner("กำลังบันทึกข้อมูล..."):
                try:
                    # 1. บันทึกลง Local CSV
                    new_data = pd.DataFrame([{
                        "วันที่ตรวจ": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "อำเภอ": district, "อายุ": age, "เพศ": gender,
                        "เบาหวาน": "เป็น" if has_diabetes else "ไม่เป็น",
                        "ความดัน": "เป็น" if has_hypertension else "ไม่เป็น",
                        "โปรตีน": protein_val, "น้ำตาล": glucose_val, "เลือด": blood_val,
                        "คะแนนความเสี่ยง": risk_score, "ผลการประเมิน": result_text
                    }])
                    
                    file_name = "ckd_database.csv"
                    if os.path.exists(file_name):
                        new_data.to_csv(file_name, mode='a', header=False, index=False)
                    else:
                        new_data.to_csv(file_name, index=False)

                    # 2. ส่งไป Google Forms (ปรับใช้ Field เดิมของคุณ แต่เติมค่าเข้าไปในฟิลด์ Note หรือดัดแปลงได้ตามสะดวก)
                    # ตรงนี้ผมใช้ฟิลด์เดิมที่คุณให้มา เพื่อไม่ให้ Form พังครับ
                    FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdmHo3tH30h7iOe0ckfoktY6aPk_R7eTAbunYy0dbqXNOWPoQ/formResponse"
                    form_data = {
                        "entry.226071067": str(district), "entry.1224620038": str(age), "entry.1030234450": str(gender),
                        "entry.853278913": "เป็น" if has_diabetes else "ไม่เป็น", "entry.1930442439": "เป็น" if has_hypertension else "ไม่เป็น",
                        "entry.853069744": str(nsaids_usage), "entry.643930526": str(protein_val), # ใช้ช่องนี้เก็บโปรตีนไปก่อน
                        "entry.19531897": str(risk_score), "entry.1594709429": str(result_text)
                    }
                    response = requests.post(FORM_URL, data=form_data)
                    
                    if response.status_code == 200:
                        st.session_state.is_submitted = True # ล็อคปุ่ม
                        st.success("✅ บันทึกข้อมูลสำเร็จ!")
                        st.toast("บันทึกข้อมูลเข้าสู่ระบบเรียบร้อย", icon="✅")
                    else:
                        st.error(f"❌ Google Forms ปฏิเสธข้อมูล (Error {response.status_code})")
                        
                except Exception as e:
                    st.error(f"❌ ไม่สามารถส่งข้อมูลได้: {e}")

        # ปุ่มเริ่มตรวจคนใหม่
        if st.session_state.is_submitted:
            if st.button("🔄 เริ่มตรวจคนต่อไป", use_container_width=True):
                # เคลียร์ค่าทั้งหมด
                st.session_state.ai_data = None
                st.session_state.is_submitted = False
                st.rerun()

# ==========================================
# ส่วนเสริม: Dashboard
# ==========================================
st.markdown("---")
with st.expander("📊 คลิกที่นี่เพื่อดู Dashboard สถิติเฝ้าระวังโรคไต", expanded=False):
    if os.path.exists("ckd_database.csv"):
        df = pd.read_csv("ckd_database.csv")
        st.dataframe(df, use_container_width=True)
            
        st.markdown("---")
        st.subheader("📈 แผนภูมิผู้ที่มีความเสี่ยง (แบ่งตามอำเภอ)")
        risk_df = df[df["ผลการประเมิน"].isin(["ความเสี่ยงสูงมาก", "ความเสี่ยงปานกลาง"])]
        if not risk_df.empty:
            st.bar_chart(risk_df["อำเภอ"].value_counts())
        else:
            st.info("ยังไม่มีผู้ป่วยที่มีความเสี่ยงในระบบ")
            
        st.markdown("---")
        if st.button("🗑️ ล้างข้อมูลทดสอบทั้งหมด", type="secondary"):
            os.remove("ckd_database.csv")
            st.session_state.ai_data = None
            st.session_state.is_submitted = False
            st.rerun()
    else:
        st.info("ยังไม่มีข้อมูลในระบบ กราฟจะแสดงผลเมื่อมีการบันทึกข้อมูลแล้วครับ")
