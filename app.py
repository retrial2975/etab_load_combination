import streamlit as st
import pandas as pd
import numpy as np

# ฟังก์ชันสำหรับคำนวณ Load Combination
def calculate_combinations(df):
    """
    ฟังก์ชันสำหรับคำนวณ Load Combination จาก DataFrame ที่รับเข้ามา
    โดยทำการ Group by 'Story', 'Column', 'Unique Name', 'Station'
    แล้วคำนวณค่าใหม่ตามสูตร U01, U02, U03
    """
    # เลือกเฉพาะคอลัมน์ที่จำเป็นสำหรับการคำนวณ
    value_cols = ['P', 'V2', 'V3', 'T', 'M2', 'M3']
    group_cols = ['Story', 'Column', 'Unique Name', 'Station']
    
    # Pivot table เพื่อให้ Output Case กลายเป็นคอลัมน์
    # ทำให้ง่ายต่อการคำนวณในแต่ละแถว
    pivot_df = df.pivot_table(index=group_cols,
                              columns='Output Case',
                              values=value_cols,
                              fill_value=0) # เติม 0 ในช่องที่ไม่มีข้อมูล

    # จัดการกับ Multi-level columns ที่เกิดจาก Pivot
    pivot_df.columns = ['_'.join(col).strip() for col in pivot_df.columns.values]
    pivot_df.reset_index(inplace=True)

    # --- การคำนวณ Load Combinations ---
    # สร้าง Dictionary เพื่อเก็บ DataFrame ของแต่ละ Combination
    combo_dfs = {}

    # ตรวจสอบว่ามีคอลัมน์ที่ต้องใช้คำนวณหรือไม่ ถ้าไม่มีให้สร้างและใส่ค่า 0
    required_cases = ['Dead', 'SDL', 'Live', 'EX', 'EY']
    for case in required_cases:
        for val in value_cols:
            col_name = f'{val}_{case}'
            if col_name not in pivot_df.columns:
                pivot_df[col_name] = 0

    # คำนวณ U01: 1.4*Dead + 1.4*SDL + 1.7*Live
    df_u01 = pivot_df[group_cols].copy()
    df_u01['Output Case'] = 'U01'
    for val in value_cols:
        df_u01[val] = (1.4 * pivot_df[f'{val}_Dead'] +
                       1.4 * pivot_df[f'{val}_SDL'] +
                       1.7 * pivot_df[f'{val}_Live'])
    combo_dfs['U01'] = df_u01

    # คำนวณ U02: 1.05*Dead + 1.05*SDL + 1.275*Live + EX
    df_u02 = pivot_df[group_cols].copy()
    df_u02['Output Case'] = 'U02'
    for val in value_cols:
        df_u02[val] = (1.05 * pivot_df[f'{val}_Dead'] +
                       1.05 * pivot_df[f'{val}_SDL'] +
                       1.275 * pivot_df[f'{val}_Live'] +
                       pivot_df[f'{val}_EX'])
    combo_dfs['U02'] = df_u02

    # คำนวณ U03: 1.05*Dead + 1.05*SDL + 1.275*Live - EX
    df_u03 = pivot_df[group_cols].copy()
    df_u03['Output Case'] = 'U03'
    for val in value_cols:
        df_u03[val] = (1.05 * pivot_df[f'{val}_Dead'] +
                       1.05 * pivot_df[f'{val}_SDL'] +
                       1.275 * pivot_df[f'{val}_Live'] -
                       pivot_df[f'{val}_EX'])
    combo_dfs['U03'] = df_u03

    # รวมผลลัพธ์ทั้งหมดเข้าด้วยกัน
    result_df = pd.concat(combo_dfs.values(), ignore_index=True)
    
    # จัดเรียงคอลัมน์ให้เหมือนเดิม
    final_cols = group_cols + ['Output Case'] + value_cols
    result_df = result_df[final_cols]

    return result_df

# --- ส่วนของหน้าเว็บ Streamlit ---

st.set_page_config(layout="wide")
st.title('โปรแกรมคำนวณ Load Combination 🏗️')

st.write("""
อัปโหลดไฟล์ `load.csv` ของคุณเพื่อคำนวณ Load Combination ใหม่ตามสูตร:
- **U01** = `1.4*Dead + 1.4*SDL + 1.7*Live`
- **U02** = `1.05*Dead + 1.05*SDL + 1.275*Live + EX`
- **U03** = `1.05*Dead + 1.05*SDL + 1.275*Live - EX`

โปรแกรมจะทำการ **Group by** จากคอลัมน์ `Story`, `Column`, `Unique Name`, และ `Station`
""")

# สร้างตัวอัปโหลดไฟล์
uploaded_file = st.file_uploader("เลือกไฟล์ load.csv", type=['csv'])

if uploaded_file is not None:
    # อ่านไฟล์ CSV ที่อัปโหลด
    try:
        input_df = pd.read_csv(uploaded_file)
        st.success("✔️ อัปโหลดไฟล์สำเร็จแล้ว!")

        st.subheader("ข้อมูลดิบจากไฟล์ที่อัปโหลด (5 แถวแรก)")
        st.dataframe(input_df.head())

        # เริ่มการคำนวณ
        with st.spinner('กำลังคำนวณ Load Combinations... ⏳'):
            result_df = calculate_combinations(input_df)
        
        st.success("✔️ คำนวณเสร็จสิ้น!")
        st.subheader("ผลลัพธ์การคำนวณ (U01, U02, U03)")
        st.dataframe(result_df)

        # สร้างปุ่มสำหรับดาวน์โหลดไฟล์ CSV
        @st.cache_data
        def convert_df_to_csv(df):
            return df.to_csv(index=False).encode('utf-8')

        csv_output = convert_df_to_csv(result_df)

        st.download_button(
            label="📥 ดาวน์โหลดผลลัพธ์เป็น CSV",
            data=csv_output,
            file_name='load_combinations_result.csv',
            mime='text/csv',
        )

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")
