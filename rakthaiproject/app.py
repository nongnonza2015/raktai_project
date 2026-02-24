import streamlit as st
import cv2
import numpy as np
import math
from PIL import Image

# ==========================================
# ส่วนที่ 1: การตั้งค่าหน้าเว็บ & เก็บข้อมูลความเสี่ยง
# ==========================================

st.set_page_config(page_title="CKD Early Detection (Dipstick)", layout="centered")

st.title("🌾 ระบบคัดกรองโรคไตเบื้องต้นสำหรับเกษตรกร")
st.markdown("ผสมผสานการวิเคราะห์แผ่นปัสสาวะ (Dipstick) ด้วย AI เข้ากับข้อมูลความเสี่ยงของผู้ป่วย")

st.header("📋 1. ข้อมูลผู้รับการตรวจ (Risk Factors)")
st.info("ข้อมูลเหล่านี้จะถูกนำไปคำนวณร่วมกับผลปัสสาวะ เพื่อประเมินความเสี่ยงที่แม่นยำขึ้น")

col1, col2 = st.columns(2)

with col1:
    age = st.number_input("อายุ (ปี)", min_value=1, max_value=120, value=45)
    gender = st.selectbox("เพศ", ["ชาย", "หญิง"])

with col2:
    # ปัจจัยเสี่ยงหลักของโรคไตในเกษตรกร
    has_disease = st.checkbox("🩺 มีโรคประจำตัว (เบาหวาน / ความดันสูง)")
    uses_nsaids = st.checkbox("💊 กินยาแก้ปวด/คลายกล้ามเนื้อ (NSAIDs) เป็นประจำ")
    chemical_expose = st.checkbox("🧪 สัมผัสสารเคมีกำจัดศัตรูพืชบ่อยครั้ง")

st.markdown("---")

# ==========================================
# ส่วนที่ 2: ระบบประมวลผลภาพ (Computer Vision)
# ==========================================
st.header("📷 2. ถ่ายภาพแผ่นทดสอบ (Dipstick)")
st.info("🎯 คำแนะนำ: นำแผ่นตรวจปัสสาวะมาจ่อที่กล้อง โดยให้ **ช่องโปรตีน (Protein)** อยู่ตรงกลาง 'กล่องโฟกัสสีเขียว' พอดี แล้วกดถ่ายรูป")

camera_photo = st.camera_input("คลิกเพื่อเปิดกล้องและถ่ายภาพ")

# ถ้ามีการถ่ายรูปแล้ว ให้ทำคำสั่งด้านล่างนี้
if camera_photo is not None:
    # 1. แปลงภาพจากกล้องให้อ่านค่าได้
    image = Image.open(camera_photo)
    img_array = np.array(image) # ภาพจาก Streamlit จะเป็น RGB อยู่แล้ว
    
    # 2. หาจุดกึ่งกลางภาพ เพื่อสร้างเป้าเล็ง
    height, width, _ = img_array.shape
    center_x, center_y = width // 2, height // 2
    box_size = 30  # ขนาดระยะจากจุดกึ่งกลาง (รวมความกว้างกล่องจะเป็น 60x60 พิกเซล)
    
    # 3. ตัดภาพ (Crop) เฉพาะในกล่องเป้าเล็งมาประมวลผล
    cropped_img = img_array[center_y - box_size : center_y + box_size, 
                            center_x - box_size : center_x + box_size]
    
    # 4. หาค่าเฉลี่ยสี RGB ในกล่องที่ตัดมา (ดูดสี)
    avg_color_per_row = np.average(cropped_img, axis=0)
    avg_color = np.average(avg_color_per_row, axis=0)
    # ปัดเศษให้เป็นตัวเลขจำนวนเต็ม
    rgb_result = (int(avg_color[0]), int(avg_color[1]), int(avg_color[2])) 
    
    st.success("📸 รับภาพสำเร็จ! ระบบทำการสกัดค่าสีเรียบร้อยแล้ว")
    
    # 5. แสดงผลการจับภาพให้ผู้ใช้ดู
    col_img1, col_img2 = st.columns(2)
    with col_img1:
        # วาดกรอบสีเขียวบนภาพต้นฉบับ
        img_with_box = img_array.copy()
        cv2.rectangle(img_with_box, 
                      (center_x - box_size, center_y - box_size), 
                      (center_x + box_size, center_y + box_size), 
                      (0, 255, 0), 3) # (0,255,0) คือสีเขียว, 3 คือความหนาเส้น
        st.image(img_with_box, caption="ภาพต้นฉบับ (เล็งให้อยู่ในกรอบสีเขียว)", use_column_width=True)
        
    with col_img2:
        st.image(cropped_img, caption="ภาพที่ AI ตัดมาวิเคราะห์", width=150)
        st.write("**🎨 สีที่ AI ดูดมาได้:**")
        
        # สร้างกล่องสีจำลอง โชว์สีของจริงที่อ่านได้
        color_box = f"<div style='width: 100px; height: 50px; background-color: rgb({rgb_result[0]}, {rgb_result[1]}, {rgb_result[2]}); border: 1px solid black; border-radius: 5px;'></div>"
        st.markdown(color_box, unsafe_allow_html=True)
        st.code(f"Red: {rgb_result[0]}\nGreen: {rgb_result[1]}\nBlue: {rgb_result[2]}")

   # ==========================================
    # ส่วนที่ 3: ระบบ AI เทียบสี (Color Matching Algorithm)
    # ==========================================
    st.markdown("---")
    st.header("🧠 3. ผลการวิเคราะห์สีปัสสาวะ (Protein Level)")
    
    # ฐานข้อมูลสีอ้างอิงของช่องโปรตีน (ตัวเลข RGB เหล่านี้เป็นการประมาณการเบื้องต้น)
    # *ในการใช้งานจริง ต้องนำแผ่นตรวจจริงมาถ่ายและจดค่า RGB เข้ามาใส่ใหม่เพื่อให้แม่นยำ 100%
    REFERENCE_COLORS = {
        "Negative (ปกติ)": (210, 220, 120),  # สีเหลืองอ่อน
        "Trace (ร่องรอย)": (170, 200, 110),  # สีเขียวอ่อนอมเหลือง
        "+1 (30 mg/dL)": (120, 180, 100),    # สีเขียว
        "+2 (100 mg/dL)": (80, 150, 100),    # สีเขียวเข้ม
        "+3 (300 mg/dL)": (50, 120, 120),    # สีเขียวอมฟ้า
        "+4 (2000+ mg/dL)": (30, 80, 100)    # สีฟ้าเข้ม
    }
    
    # ฟังก์ชันคำนวณระยะห่างของสี (หาสีที่ใกล้เคียงที่สุด)
    def get_closest_color(target_rgb, color_dict):
        min_distance = float('inf')
        closest_label = None
        for label, ref_rgb in color_dict.items():
            # ใช้คณิตศาสตร์หาระยะห่างของสี $\sqrt{(R_1-R_2)^2 + (G_1-G_2)^2 + (B_1-B_2)^2}$
            distance = math.sqrt((target_rgb[0] - ref_rgb[0])**2 + 
                                 (target_rgb[1] - ref_rgb[1])**2 + 
                                 (target_rgb[2] - ref_rgb[2])**2)
            if distance < min_distance:
                min_distance = distance
                closest_label = label
        return closest_label

    # เรียกใช้งาน AI เพื่อเทียบสี
    matched_result = get_closest_color(rgb_result, REFERENCE_COLORS)
    st.info(f"🔬 **ระดับโปรตีนที่ AI อ่านได้คือ:** `{matched_result}`")


    # ==========================================
    # ส่วนที่ 4: ระบบวิเคราะห์ความเสี่ยง (Risk Scoring)
    # ==========================================
    st.header("🚨 4. สรุปผลความเสี่ยงโรคไต (CKD Risk Score)")
    
    risk_score = 0
    
    # 1. ให้คะแนนจากผลตรวจปัสสาวะ
    if "Negative" not in matched_result:
        if "Trace" in matched_result:
            risk_score += 1
        elif "+1" in matched_result or "+2" in matched_result:
            risk_score += 3
        else:
            risk_score += 4  # กรณี +3 หรือ +4 ถือว่ารั่วหนักมาก
            
    # 2. ให้คะแนนจากประวัติ (ดึงข้อมูลมาจากส่วนที่ 1 ด้านบน)
    if has_disease:
        risk_score += 2
    if uses_nsaids:
        risk_score += 2
    if chemical_expose:
        risk_score += 1
    if age >= 50:
        risk_score += 1

    # 3. แสดงผลลัพธ์แบบเข้าใจง่ายสำหรับเกษตรกร
    st.subheader("ผลการประเมิน:")
    if risk_score >= 5:
        st.error("🔴 **ความเสี่ยงสูงมาก (High Risk):** พบสัญญาณโปรตีนรั่วและมีปัจจัยเสี่ยงร่วม แนะนำให้ไปพบแพทย์เพื่อตรวจค่าไต (eGFR) ที่โรงพยาบาลโดยเร็ว!")
    elif risk_score >= 3:
        st.warning("🟡 **ความเสี่ยงปานกลาง (Moderate Risk):** ไตอาจเริ่มทำงานหนัก ควรปรับพฤติกรรม ดื่มน้ำมากๆ ลดเค็ม/ลดยาแก้ปวด และตรวจซ้ำใน 1-2 สัปดาห์")
    else:
        st.success("🟢 **ความเสี่ยงต่ำ (Low Risk):** ปกติดี! รักษาสุขภาพต่อไปและตรวจเช็คปีละครั้ง")
        
    st.markdown("---")
    st.caption("💡 หมายเหตุ: แอปพลิเคชันนี้เป็นเพียงเครื่องมือคัดกรองเบื้องต้น ไม่สามารถใช้แทนการวินิจฉัยของแพทย์ได้")