import streamlit as st
import cv2
import numpy as np
import math
from PIL import Image
import pandas as pd  
import os            
from datetime import datetime 
import requests  

# ==========================================
# ส่วนที่ 1: การตั้งค่าหน้าเว็บ & เก็บข้อมูลความเสี่ยง
# ==========================================
st.set_page_config(page_title="CKD Early Detection (Dipstick)", layout="centered")

st.title("🌾 ระบบคัดกรองโรคไตเบื้องต้นสำหรับเกษตรกรในจังหวัดสกลนคร")
st.markdown("ผสมผสานการวิเคราะห์แผ่นปัสสาวะ (Dipstick) ด้วย AI เข้ากับข้อมูลความเสี่ยงของผู้ป่วย")

st.header("📋 1. ข้อมูลผู้รับการตรวจ (Risk Factors)")
st.info("ข้อมูลเหล่านี้จะถูกนำไปคำนวณร่วมกับผลปัสสาวะ เพื่อประเมินความเสี่ยงที่แม่นยำขึ้น")

col1, col2 = st.columns(2)

with col1:
    age = st.number_input("อายุ (ปี)", min_value=1, max_value=120, value=45)
    gender = st.selectbox("เพศ", ["ชาย", "หญิง"])

st.markdown("---")
st.subheader("📍 พื้นที่ปฏิบัติงาน (สำหรับ อสม. / รพ.สต.)")
district = st.selectbox("เลือกอำเภอที่ลงพื้นที่คัดกรอง", 
                        ["อำเภอเมืองสกลนคร", "อำเภอกุสุมาลย์", "อำเภอพรรณานิคม", "อำเภอพังโคน", "อื่นๆ"])

st.markdown("**🩺 ข้อมูลสุขภาพเพิ่มเติม (ตัวแปรความเสี่ยงโรคไต)**")
col3, col4 = st.columns(2)
with col3:
    st.write("โรคประจำตัว:")
    has_diabetes = st.checkbox("โรคเบาหวาน")             
    has_hypertension = st.checkbox("โรคความดันโลหิตสูง")
with col4:
    st.write("ประวัติการใช้ยาแก้ปวด (ยาชุด/NSAIDs):")
    nsaids_usage = st.radio("ความถี่ในการกินยาแก้ปวด", ["ไม่เคยกิน / กินนานๆ ครั้ง", "กินประจำ (มากกว่า 2 ครั้ง/สัปดาห์)"], label_visibility="collapsed")

st.markdown("---")

# ==========================================
# ส่วนที่ 2: ระบบประมวลผลภาพ (Computer Vision)
# ==========================================
st.header("📷 2. ถ่ายภาพแผ่นทดสอบ (Dipstick)")
st.info("🎯 คำแนะนำ: นำแผ่นตรวจปัสสาวะมาจ่อที่กล้อง โดยให้ **ช่องโปรตีน (Protein)** อยู่ตรงกลาง 'กล่องโฟกัสสีเขียว' พอดี แล้วกดถ่ายรูป")

camera_photo = st.camera_input("คลิกเพื่อเปิดกล้องและถ่ายภาพ")

if camera_photo is not None:
    image = Image.open(camera_photo)
    img_array = np.array(image) 
    
    height, width, _ = img_array.shape
    center_x, center_y = width // 2, height // 2
    box_size = 30  
    
    cropped_img = img_array[center_y - box_size : center_y + box_size, 
                            center_x - box_size : center_x + box_size]
    
    avg_color_per_row = np.average(cropped_img, axis=0)
    avg_color = np.average(avg_color_per_row, axis=0)
    rgb_result = (int(avg_color[0]), int(avg_color[1]), int(avg_color[2])) 
    
    st.success("📸 รับภาพสำเร็จ! ระบบทำการสกัดค่าสีเรียบร้อยแล้ว")
    
    col_img1, col_img2 = st.columns(2)
    with col_img1:
        img_with_box = img_array.copy()
        cv2.rectangle(img_with_box, 
                      (center_x - box_size, center_y - box_size), 
                      (center_x + box_size, center_y + box_size), 
                      (0, 255, 0), 3) 
        st.image(img_with_box, caption="ภาพต้นฉบับ (เล็งให้อยู่ในกรอบสีเขียว)", use_column_width=True)
        
    with col_img2:
        st.image(cropped_img, caption="ภาพที่ AI ตัดมาวิเคราะห์", width=150)
        st.write("**🎨 สีที่ AI ดูดมาได้:**")
        color_box = f"<div style='width: 100px; height: 50px; background-color: rgb({rgb_result[0]}, {rgb_result[1]}, {rgb_result[2]}); border: 1px solid black; border-radius: 5px;'></div>"
        st.markdown(color_box, unsafe_allow_html=True)
        st.code(f"Red: {rgb_result[0]}\nGreen: {rgb_result[1]}\nBlue: {rgb_result[2]}")

    # ==========================================
    # ส่วนที่ 3: ระบบ AI เทียบสี 
    # ==========================================
    st.markdown("---")
    st.header("🧠 3. ผลการวิเคราะห์สีปัสสาวะ (Protein Level)")
    
    REFERENCE_COLORS = {
        "Negative (ปกติ)": (210, 220, 120),  
        "Trace (ร่องรอย)": (170, 200, 110),  
        "+1 (30 mg/dL)": (120, 180, 100),    
        "+2 (100 mg/dL)": (80, 150, 100),    
        "+3 (300 mg/dL)": (50, 120, 120),    
        "+4 (2000+ mg/dL)": (30, 80, 100)    
    }
    
    def get_closest_color(target_rgb, color_dict):
        min_distance = float('inf')
        closest_label = None
        for label, ref_rgb in color_dict.items():
            distance = math.sqrt((target_rgb[0] - ref_rgb[0])**2 + 
                                 (target_rgb[1] - ref_rgb[1])**2 + 
                                 (target_rgb[2] - ref_rgb[2])**2)
            if distance < min_distance:
                min_distance = distance
                closest_label = label
        return closest_label

    matched_result = get_closest_color(rgb_result, REFERENCE_COLORS)
    st.info(f"🔬 **ระดับโปรตีนที่ AI อ่านได้คือ:** `{matched_result}`")

    # ==========================================
    # ส่วนที่ 4: ระบบวิเคราะห์ความเสี่ยง (Risk Scoring)
    # ==========================================
    st.header("🚨 4. สรุปผลความเสี่ยงโรคไต (CKD Risk Score)")
    
    risk_score = 0
    
    if age >= 60:
        risk_score += 1

    if has_diabetes:
        risk_score += 2   
    if has_hypertension:
        risk_score += 1   

    if nsaids_usage == "กินประจำ (มากกว่า 2 ครั้ง/สัปดาห์)":
        risk_score += 2   

    if "Trace" in matched_result or "+1" in matched_result:
        risk_score += 2
    elif "+2" in matched_result or "+3" in matched_result or "+4" in matched_result:
        risk_score += 4

    result_text = "ปกติ" 

    st.subheader("ผลการประเมิน:")
    if risk_score >= 5:
        result_text = "ความเสี่ยงสูง"
        st.error("🔴 **ความเสี่ยงสูงมาก (High Risk):** พบสัญญาณโปรตีนรั่วและมีปัจจัยเสี่ยงร่วม แนะนำให้ไปพบแพทย์เพื่อตรวจค่าไต (eGFR) ที่โรงพยาบาลโดยเร็ว!")
    elif risk_score >= 3:
        result_text = "ความเสี่ยงปานกลาง"
        st.warning("🟡 **ความเสี่ยงปานกลาง (Moderate Risk):** ไตอาจเริ่มทำงานหนัก ควรปรับพฤติกรรม ดื่มน้ำมากๆ ลดเค็ม/ลดยาแก้ปวด และตรวจซ้ำใน 1-2 สัปดาห์")
    else:
        result_text = "ปกติ"
        st.success("🟢 **ความเสี่ยงต่ำ (Low Risk):** ปกติดี! รักษาสุขภาพต่อไปและตรวจเช็คปีละครั้ง")
        
    st.markdown("---")
    st.caption("💡 หมายเหตุ: แอปพลิเคชันนี้เป็นเพียงเครื่องมือคัดกรองเบื้องต้น ไม่สามารถใช้แทนการวินิจฉัยของแพทย์ได้")

    # ==========================================
    # ส่วนที่ 5: บันทึกข้อมูล
    # ==========================================
    st.markdown("---")
    st.header("💾 5. บันทึกข้อมูลลงฐานข้อมูลส่วนกลาง")
    
    if st.button("📥 บันทึกผลการคัดกรองเคสนี้"):
        with st.spinner("กำลังส่งข้อมูล..."):
            try:
                new_data = pd.DataFrame([{
                    "วันที่ตรวจ": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "อำเภอ": district,
                    "อายุ": age,
                    "เพศ": gender,
                    "เบาหวาน": "เป็น" if has_diabetes else "ไม่เป็น",
                    "ความดัน": "เป็น" if has_hypertension else "ไม่เป็น",
                    "ใช้ยาแก้ปวด": nsaids_usage,
                    "ระดับโปรตีน": matched_result,
                    "คะแนนความเสี่ยง": risk_score,
                    "ผลการประเมิน": result_text
                }])
                
                if os.path.exists("ckd_database.csv"):
                    new_data.to_csv("ckd_database.csv", mode='a', header=False, index=False)
                else:
                    new_data.to_csv("ckd_database.csv", index=False)

                FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdmHo3tH30h7iOe0ckfoktY6aPk_R7eTAbunYy0dbqXNOWPoQ/formResponse"
                
                form_data = {
                    "entry.226071067": district,
                    "entry.1224620038": age,
                    "entry.1030234450": gender,
                    "entry.853278913": "เป็น" if has_diabetes else "ไม่เป็น",
                    "entry.1930442439": "เป็น" if has_hypertension else "ไม่เป็น",
                    "entry.853069744": nsaids_usage,
                    "entry.643930526": matched_result,
                    "entry.19531897": risk_score,
                    "entry.1594709429": result_text
                }
                
                response = requests.post(FORM_URL, data=form_data)
                
                if response.status_code == 200:
                    st.success("✅ บันทึกข้อมูลขึ้น Google Sheets และระบบ Dashboard สำเร็จแล้ว!")
                    st.balloons() 
                else:
                    st.error(f"❌ Google Forms ปฏิเสธข้อมูล (Error {response.status_code})")
                    
            except Exception as e:
                st.error(f"❌ ไม่สามารถเชื่อมต่ออินเทอร์เน็ตได้: {e}")

# ==========================================
# ส่วนเสริม: แสดง Dashboard สถิติ
# ==========================================
st.markdown("---")
st.header("📊 Dashboard เฝ้าระวังโรคไตระดับอำเภอ")

if os.path.exists("ckd_database.csv"):
    df = pd.read_csv("ckd_database.csv")
    
    with st.expander("ดูตารางข้อมูลดิบทั้งหมด (Excel)"):
        st.dataframe(df)
        
    st.subheader("📈 แผนภูมิผู้ที่มีความเสี่ยงสูง (แบ่งตามอำเภอ)")
    risk_df = df[df["ผลการประเมิน"].isin(["ความเสี่ยงสูง", "ความเสี่ยงปานกลาง"])]
    
    if not risk_df.empty:
        district_counts = risk_df["อำเภอ"].value_counts()
        st.bar_chart(district_counts)
    else:
        st.info("ยังไม่มีผู้ป่วยที่มีความเสี่ยงในระบบ")
        
    if st.button("🗑️ ล้างข้อมูลทดสอบทั้งหมด"):
        os.remove("ckd_database.csv")
        st.rerun()
else:
    st.info("ยังไม่มีข้อมูลในระบบ ลองทดสอบบันทึกข้อมูลดูสิครับ กราฟถึงจะแสดงผล!")

