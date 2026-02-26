import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd  
import os            
from datetime import datetime 
import requests  

# ==========================================
# ตั้งค่า API ของ Gemini (สมอง AI)
# ==========================================
# ⚠️ นำ API Key ของคุณมาใส่ตรงนี้ (แนะนำให้เปลี่ยนคีย์ใหม่หลังทดสอบเสร็จ)
API_KEY = "AIzaSyDvsHoM1Kvg4O8IP7uXZxfXO34DFTnRIi8" 
genai.configure(api_key=API_KEY)
# เลือกใช้รุ่น Flash เพราะอ่านรูปเก่งและทำงานเร็วมาก
ai_model = genai.GenerativeModel('gemini-1.5-flash')

# ==========================================
# ส่วนที่ 1: การตั้งค่าหน้าเว็บ & ข้อมูลผู้รับการตรวจ
# ==========================================
st.set_page_config(page_title="CKD AI Scanner", layout="centered")

st.title("🌾 ระบบคัดกรองโรคไตสำหรับเกษตรกรในจังหวัดสกลนคร")
st.markdown("ใช้ Gemini AI วิเคราะห์แผ่นปัสสาวะ (โปรตีน, เลือด, น้ำตาล) พร้อมประเมินความเสี่ยง")

st.header("📋 1. ข้อมูลผู้รับการตรวจ (Risk Factors)")
col1, col2 = st.columns(2)
with col1:
    age = st.number_input("อายุ (ปี)", min_value=1, max_value=120, value=45)
    gender = st.selectbox("เพศ", ["ชาย", "หญิง"])

district = st.selectbox("📍 เลือกอำเภอที่ลงพื้นที่", 
                        ["อำเภอเมืองสกลนคร", "อำเภอกุสุมาลย์", "อำเภอพรรณานิคม", "อำเภอพังโคน", "อื่นๆ"])

st.markdown("**🩺 ปัจจัยเสี่ยงโรคไต:**")
col3, col4 = st.columns(2)
with col3:
    has_diabetes = st.checkbox("โรคเบาหวาน")             
    has_hypertension = st.checkbox("โรคความดันโลหิตสูง")
    nsaids_usage = st.radio("การใช้ยาแก้ปวด/ยาชุด:", ["ไม่ค่อยกิน", "กินประจำ (มากกว่า 2 ครั้ง/สัปดาห์)"])

with col4:
    has_stones = st.checkbox("🪨 ประวัติโรคนิ่ว / ปัสสาวะขัด")
    high_sodium = st.checkbox("🧂 ทานเค็มจัด / ปลาร้า / ผงชูรสเยอะ")
    chemical_exposure = st.checkbox("🧪 สัมผัสสารเคมีเกษตรเป็นประจำ")

st.markdown("---")

# ==========================================
# ส่วนที่ 2: กล้องถ่ายภาพ
# ==========================================
st.header("📷 2. ถ่ายภาพแผ่นทดสอบ (Dipstick)")
st.info("💡 ถือแผ่นตรวจให้เห็นแถบสีชัดเจนแล้วกดถ่ายภาพ")

img_file = st.camera_input("📸 ถ่ายภาพแผ่นตรวจ")

# ==========================================
# ส่วนที่ 3: ระบบ Gemini AI อ่านค่า 3 แถบ
# ==========================================
if img_file is not None:
    st.markdown("---")
    st.header("🧠 3. ผลการวิเคราะห์ด้วย Gemini AI")
    
    # เปิดรูปภาพเตรียมส่งให้ AI
    image = Image.open(img_file)
    st.image(image, caption="ภาพแผ่นตรวจที่ส่งให้ AI วิเคราะห์", use_container_width=True)
    
    ai_result_text = ""
    
    with st.spinner("🤖 AI กำลังเพ่งมองแถบสีทั้ง 3 ค่า... กรุณารอสักครู่..."):
        try:
            # คำสั่ง (Prompt) ที่สั่งให้ AI ทำงาน
            prompt = """
            คุณคือแพทย์ผู้เชี่ยวชาญด้านการอ่านแผ่นตรวจปัสสาวะ (Urine Dipstick)
            ในภาพนี้คือแผ่นตรวจ กรุณาวิเคราะห์แถบสี 3 ค่า เรียงจากบนลงล่าง:
            1. โปรตีน (Protein)
            2. เม็ดเลือดแดง (Blood)
            3. น้ำตาล (Glucose)
            
            รูปแบบการตอบ:
            - โปรตีน: [ตอบแค่ Negative, Trace, +1, +2, +3, หรือ +4]
            - เม็ดเลือดแดง: [ตอบผลลัพธ์ที่เห็น]
            - น้ำตาล: [ตอบผลลัพธ์ที่เห็น]
            - สรุปคำแนะนำสั้นๆ 1 ประโยค
            """
            
            # ส่งรูปและคำสั่งไปให้ Gemini
            response = ai_model.generate_content([prompt, image])
            ai_result_text = response.text
            
            st.success("✨ วิเคราะห์เสร็จสิ้น!")
            st.markdown(f"> **คำตอบจาก AI:**\n\n{ai_result_text}")
            
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อ AI: {e}")
            st.stop() # หยุดการทำงานถ้าระบบ AI ล่ม

    # ==========================================
    # ส่วนที่ 4: ระบบวิเคราะห์ความเสี่ยงรวม
    # ==========================================
    st.markdown("---")
    st.header("🚨 4. สรุปผลการประเมินความเสี่ยง")

    # คำนวณคะแนนพื้นฐานจากข้อมูลผู้ป่วย
    risk_score = 0
    if age >= 60: risk_score += 1
    if has_diabetes: risk_score += 2
    if has_hypertension: risk_score += 1
    if nsaids_usage == "กินประจำ (มากกว่า 2 ครั้ง/สัปดาห์)": risk_score += 2
    if has_stones: risk_score += 2
    if high_sodium: risk_score += 1
    if chemical_exposure: risk_score += 1

    # ดึงข้อมูลจากข้อความที่ AI ตอบมาเพื่อคิดคะแนนเพิ่ม (ดักจับคำ)
    if "+1" in ai_result_text or "Trace" in ai_result_text:
        risk_score += 2
    if "+2" in ai_result_text or "+3" in ai_result_text or "+4" in ai_result_text:
        risk_score += 4
    if "เลือด" in ai_result_text and ("+" in ai_result_text or "Positive" in ai_result_text):
        risk_score += 2 # ถ้ามีเลือดปน ให้บวกความเสี่ยงเพิ่ม

    # ประเมินผลลัพธ์
    if risk_score >= 7:
        result_text, status_color, st_function = "ความเสี่ยงสูงมาก", "🔴", st.error
    elif 4 <= risk_score <= 6:
        result_text, status_color, st_function = "ความเสี่ยงปานกลาง", "🟡", st.warning
    else:
        result_text, status_color, st_function = "ความเสี่ยงต่ำ / ปกติ", "🟢", st.success

    with st.container():
        m1, m2 = st.columns(2)
        m1.metric(label="คะแนนความเสี่ยงรวม", value=f"{risk_score} คะแนน")
        with m2:
            st.write("**สถานะปัจจุบัน**")
            st.markdown(f"### {status_color} {result_text}")
        st_function(f"ผลสรุป: {result_text}")

    # ==========================================
    # ส่วนที่ 5: บันทึกข้อมูลและเก็บภาพ
    # ==========================================
    st.markdown("---")
    st.header("💾 5. บันทึกข้อมูล")
    
    if st.button("📥 บันทึกผลและเซฟรูปภาพเคสนี้"):
        with st.spinner("กำลังจัดเก็บข้อมูล..."):
            try:
                # 1. เซฟรูปภาพ
                if not os.path.exists("captured_images"):
                    os.makedirs("captured_images")
                
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                image_filename = f"dipstick_{timestamp_str}.jpg"
                image_path = os.path.join("captured_images", image_filename)
                
                # บันทึกภาพที่ถ่ายไว้ด้วย PIL (สีไม่เพี้ยนแบบ OpenCV)
                image.save(image_path)

                # 2. บันทึกลง Local CSV
                new_data = pd.DataFrame([{
                    "วันที่เวลา": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "อำเภอ": district, "อายุ": age, "เพศ": gender,
                    "คะแนนรวม": risk_score, "สถานะ": result_text,
                    "ผลจาก AI": ai_result_text.replace("\n", " "), # เอาขึ้นบรรทัดใหม่ออกเพื่อให้ลง Excel สวยๆ
                    "ชื่อไฟล์ภาพ": image_filename
                }])
                
                if os.path.exists("ckd_database.csv"):
                    new_data.to_csv("ckd_database.csv", mode='a', header=False, index=False)
                else:
                    new_data.to_csv("ckd_database.csv", index=False)

                st.success(f"✅ บันทึกข้อมูลและภาพถ่าย ({image_filename}) สำเร็จ!")
                st.balloons() 
                    
            except Exception as e:
                st.error(f"❌ เกิดข้อผิดพลาด: {e}")

# ==========================================
# Dashboard สถิติ
# ==========================================
st.markdown("---")
if os.path.exists("ckd_database.csv"):
    df = pd.read_csv("ckd_database.csv")
    with st.expander("ดูตารางข้อมูลที่บันทึกไว้"):
        st.dataframe(df)

