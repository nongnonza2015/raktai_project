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
# ส่วนที่ 2: ระบบกล้องถ่ายภาพ (ไม่ต้องใช้ av/webrtc)
# ==========================================
st.header("📷 2. เล็งและถ่ายภาพแผ่นทดสอบ (Dipstick)")
st.info("💡 วิธีใช้: ถือแผ่นตรวจให้แนวตั้งตรงกับกลางหน้าจอ แล้วกดถ่ายภาพ (ระบบจะตีกรอบวิเคราะห์ให้อัตโนมัติหลังกดถ่าย)")

# ใช้คำสั่งกล้องมาตรฐานของ Streamlit
img_file = st.camera_input("📸 ส่องแผ่นตรวจให้ตรงเป้าแล้วกดถ่ายภาพ")

# ==========================================
# ส่วนที่ 3: ระบบ AI เทียบสี (Protein Level) ทำงานเมื่อกดถ่ายรูป
# ==========================================
if img_file is not None:
    st.markdown("---")
    st.header("🧠 3. ผลการวิเคราะห์สีปัสสาวะ (Protein Level)")
    
    # อ่านภาพที่ถ่ายได้ด้วย Pillow แล้วแปลงเป็น Array แบบ RGB
    image = Image.open(img_file)
    img_array = np.array(image)
    
    h, w, _ = img_array.shape
    cx, cy = w // 2, h // 2

    # --- โชว์ภาพพร้อมวาดกรอบให้ผู้ใช้ดูว่า AI เล็งตรงไหน ---
    st.subheader("🎯 ตำแหน่งที่ AI ดึงข้อมูลสีไปวิเคราะห์")
    preview_img = img_array.copy()
    # วาดกล่องสีเขียว (ช่องโปรตีน) ตรงกลาง
    cv2.rectangle(preview_img, (cx-20, cy-20), (cx+20, cy+20), (0, 255, 0), 3) 
    # วาดกล่องสีขาว (จุดอ้างอิงแสง) เยื้องไปทางขวา
    cv2.rectangle(preview_img, (cx+40, cy-20), (cx+60, cy+20), (255, 255, 255), 3)
    
    # แสดงรูปภาพที่วาดกรอบแล้ว
    st.image(preview_img, caption="กรอบสีเขียว = ช่องโปรตีน | กรอบสีขาว = จุดเทียบแสง")
    
    # --- ตัดภาพเพื่อเอาสีไปคำนวณ ---
    # 1. ตัดภาพส่วน "ช่องสีโปรตีน" (ตรงกลาง)
    protein_box = img_array[cy-20:cy+20, cx-20:cx+20]
    avg_p = np.average(np.average(protein_box, axis=0), axis=0)
    raw_rgb = (int(avg_p[0]), int(avg_p[1]), int(avg_p[2]))

    # 2. ตัดภาพส่วน "ขอบสีขาว" 
    white_box = img_array[cy-20:cy+20, cx+40:cx+60] 
    avg_w = np.average(np.average(white_box, axis=0), axis=0)
    white_rgb = (int(avg_w[0]), int(avg_w[1]), int(avg_w[2]))

    # ฟังก์ชันปรับค่าแสง (White Balance)
    def apply_white_balance(target_rgb, white_ref_rgb):
        r_scale = 255.0 / max(white_ref_rgb[0], 1)
        g_scale = 255.0 / max(white_ref_rgb[1], 1)
        b_scale = 255.0 / max(white_ref_rgb[2], 1)
        
        new_r = min(int(target_rgb[0] * r_scale), 255)
        new_g = min(int(target_rgb[1] * g_scale), 255)
        new_b = min(int(target_rgb[2] * b_scale), 255)
        return (new_r, new_g, new_b)

    # 3. คำนวณ White Balance
    balanced_rgb = apply_white_balance(raw_rgb, white_rgb)

    # ตารางค่าสีอ้างอิงมาตรฐาน (RGB) 
    REFERENCE_COLORS = {
        "Negative (ปกติ)": (205, 225, 130),  
        "Trace (ร่องรอย)": (185, 210, 125),  
        "+1 (30 mg/dL)": (145, 190, 120),    
        "+2 (100 mg/dL)": (100, 165, 120),   
        "+3 (300 mg/dL)": (65, 135, 130),    
        "+4 (2000+ mg/dL)": (40, 95, 115)    
    }
    
    def get_closest_color(target_rgb, color_dict):
        min_distance = float('inf')
        closest_label = "ไม่สามารถระบุได้"
        for label, ref_rgb in color_dict.items():
            distance = math.sqrt(sum((target_rgb[i] - ref_rgb[i])**2 for i in range(3)))
            if distance < min_distance:
                min_distance = distance
                closest_label = label
        return closest_label

    # วิเคราะห์สี
    matched_result = get_closest_color(balanced_rgb, REFERENCE_COLORS)
    st.success(f"🔬 **ระดับโปรตีนที่ AI วิเคราะห์ได้:** `{matched_result}`")
    
    # เพิ่มแถบสีเปรียบเทียบ
    st.write("📊 **แถบสีมาตรฐานเปรียบเทียบ:**")
    cols = st.columns(6)
    for i, (label, color) in enumerate(REFERENCE_COLORS.items()):
        with cols[i]:
            st.markdown(f"<div style='background-color: rgb{color}; height: 20px; border-radius: 3px; border: 1px solid #ddd;'></div>", unsafe_allow_html=True)
            st.caption(label)

    # ==========================================
    # ส่วนที่ 4: ระบบวิเคราะห์ความเสี่ยง (Risk Scoring) 
    # ==========================================
    st.markdown("---")
    st.header("🚨 4. สรุปผลการประเมินความเสี่ยง")

    # 1. คำนวณคะแนน 
    risk_score = 0
    if age >= 60: risk_score += 1
    if has_diabetes: risk_score += 2
    if has_hypertension: risk_score += 1
    if nsaids_usage == "กินประจำ (มากกว่า 2 ครั้ง/สัปดาห์)": risk_score += 2

    if "Trace" in matched_result or "+1" in matched_result: risk_score += 2
    elif any(x in matched_result for x in ["+2", "+3", "+4"]): risk_score += 4

    # 2. กำหนดสถานะและสี
    if risk_score >= 6:
        result_text, status_color, st_function = "ความเสี่ยงสูงมาก", "🔴", st.error
        advice = "🚨 **ข้อแนะนำ:** ควรส่งต่อพบแพทย์เพื่อเจาะเลือดตรวจค่าไต (eGFR) ทันที"
    elif 4 <= risk_score <= 5:
        result_text, status_color, st_function = "ความเสี่ยงปานกลาง", "🟡", st.warning
        advice = "⚠️ **ข้อแนะนำ:** ควรลดอาหารเค็ม เลิกใช้ยาแก้ปวด และนัดตรวจปัสสาวะซ้ำใน 2 สัปดาห์"
    else:
        result_text, status_color, st_function = "ความเสี่ยงต่ำ / ปกติ", "🟢", st.success
        advice = "✅ **ข้อแนะนำ:** รักษาพฤติกรรมสุขภาพที่ดี ดื่มน้ำให้เพียงพอ และตรวจสุขภาพประจำปี"

    # 3. แสดง Dashboard ส่วนตัว
    with st.container():
        m1, m2, m3 = st.columns(3)
        m1.metric(label="ระดับโปรตีน", value=matched_result)
        m2.metric(label="คะแนนความเสี่ยง", value=f"{risk_score} คะแนน")
        with m3:
            st.write("**สถานะปัจจุบัน**")
            st.markdown(f"### {status_color} {result_text}")

        st_function(f"### ผลสรุป: {result_text}")
        
        with st.expander("📝 รายละเอียดการประเมินและคำแนะนำ"):
            st.markdown(advice)
            st.write(f"วิเคราะห์สำหรับผู้ป่วยเพศ {gender} อายุ {age} ปี")
            if has_diabetes or has_hypertension:
                st.write("📌 ปัจจัยเร่ง: มีโรคประจำตัว (เบาหวาน/ความดัน)")

    # ==========================================
    # ส่วนที่ 5: บันทึกข้อมูล (ปรับปรุงปุ่มให้ชัดขึ้น)
    # ==========================================
    st.markdown("---")
    st.header("💾 5. บันทึกข้อมูลลงฐานข้อมูลส่วนกลาง")
    
    # เพิ่ม type="primary" และ use_container_width=True เพื่อให้ปุ่มใหญ่และสีเด่นชัด
    if st.button("📥 ยืนยันและบันทึกผลการคัดกรองเคสนี้", type="primary", use_container_width=True):
        with st.spinner("กำลังส่งข้อมูล..."):
            try:
                # 1. บันทึกลง Local CSV
                new_data = pd.DataFrame([{
                    "วันที่ตรวจ": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "อำเภอ": district, "อายุ": age, "เพศ": gender,
                    "เบาหวาน": "เป็น" if has_diabetes else "ไม่เป็น",
                    "ความดัน": "เป็น" if has_hypertension else "ไม่เป็น",
                    "ใช้ยาแก้ปวด": nsaids_usage, "ระดับโปรตีน": matched_result,
                    "คะแนนความเสี่ยง": risk_score, "ผลการประเมิน": result_text
                }])
                
                if os.path.exists("ckd_database.csv"):
                    new_data.to_csv("ckd_database.csv", mode='a', header=False, index=False)
                else:
                    new_data.to_csv("ckd_database.csv", index=False)

                # 2. ส่งไป Google Forms 
                FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdmHo3tH30h7iOe0ckfoktY6aPk_R7eTAbunYy0dbqXNOWPoQ/formResponse"
                form_data = {
                    "entry.226071067": str(district), "entry.1224620038": str(age), "entry.1030234450": str(gender),
                    "entry.853278913": "เป็น" if has_diabetes else "ไม่เป็น", "entry.1930442439": "เป็น" if has_hypertension else "ไม่เป็น",
                    "entry.853069744": str(nsaids_usage), "entry.643930526": str(matched_result),
                    "entry.19531897": str(risk_score), "entry.1594709429": str(result_text)
                }
                
                response = requests.post(FORM_URL, data=form_data)
                
                if response.status_code == 200:
                    st.success("✅ บันทึกข้อมูลขึ้น Google Sheets และระบบ Dashboard สำเร็จแล้ว!")
                    # เปลี่ยนจากลูกโป่ง (st.balloons) เป็น Toast notification ที่ดูเป็นทางการ
                    st.toast("บันทึกข้อมูลเข้าสู่ระบบเรียบร้อย", icon="✅")
                else:
                    st.error(f"❌ Google Forms ปฏิเสธข้อมูล (Error {response.status_code})")
                    
            except Exception as e:
                st.error(f"❌ ไม่สามารถส่งข้อมูลได้: {e}")

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
    risk_df = df[df["ผลการประเมิน"].isin(["ความเสี่ยงสูงมาก", "ความเสี่ยงปานกลาง"])]
    
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
