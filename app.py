import streamlit as st
import pandas as pd
import numpy as np
import re

# --- ส่วนของการคำนวณ ---
# (ฟังก์ชัน calculate_combinations เหมือนเดิมทุกประการ)
def calculate_combinations(df, custom_story_name=None):
    value_cols = ['P', 'V2', 'V3', 'T', 'M2', 'M3']
    group_cols = ['Story', 'Column', 'Unique Name', 'Station']
    
    if custom_story_name:
        df['Story'] = custom_story_name
        
    pivot_df = df.pivot_table(index=group_cols, columns='Output Case', values=value_cols, fill_value=0)
    pivot_df.columns = ['_'.join(map(str, col)).strip() for col in pivot_df.columns.values]
    pivot_df.reset_index(inplace=True)

    required_cases = ['Dead', 'SDL', 'Live', 'EX', 'EY']
    for case in required_cases:
        for val in value_cols:
            col_name = f'{val}_{case}'
            if col_name not in pivot_df.columns:
                pivot_df[col_name] = 0

    combo_dfs = {}
    
    combinations = {
        'U01': {'Dead': 1.4, 'SDL': 1.4, 'Live': 1.7, 'EX': 0, 'EY': 0},
        'U02': {'Dead': 1.05, 'SDL': 1.05, 'Live': 1.275, 'EX': 1, 'EY': 0},
        'U03': {'Dead': 1.05, 'SDL': 1.05, 'Live': 1.275, 'EX': -1, 'EY': 0},
        'U04': {'Dead': 1.05, 'SDL': 1.05, 'Live': 1.275, 'EX': 0, 'EY': 1},
        'U05': {'Dead': 1.05, 'SDL': 1.05, 'Live': 1.275, 'EX': 0, 'EY': -1},
        'U06': {'Dead': 0.9, 'SDL': 0.9, 'Live': 0, 'EX': 1, 'EY': 0},
        'U07': {'Dead': 0.9, 'SDL': 0.9, 'Live': 0, 'EX': -1, 'EY': 0},
        'U08': {'Dead': 0.9, 'SDL': 0.9, 'Live': 0, 'EX': 0, 'EY': 1},
        'U09': {'Dead': 0.9, 'SDL': 0.9, 'Live': 0, 'EX': 0, 'EY': -1},
    }

    for name, factors in combinations.items():
        temp_df = pivot_df[group_cols].copy()
        temp_df['Output Case'] = name
        for val in value_cols:
            ex_factor = factors['EX']
            ey_factor = factors['EY']
            if val in ['V2', 'V3']:
                ex_factor *= 2.5
                ey_factor *= 2.5

            temp_df[val] = (factors['Dead'] * pivot_df[f'{val}_Dead'] +
                            factors['SDL'] * pivot_df[f'{val}_SDL'] +
                            factors['Live'] * pivot_df[f'{val}_Live'] +
                            ex_factor * pivot_df[f'{val}_EX'] +
                            ey_factor * pivot_df[f'{val}_EY'])
        combo_dfs[name] = temp_df

    result_df = pd.concat(combo_dfs.values(), ignore_index=True)
    
    for col in value_cols:
        result_df[col] = result_df[col].round(4)
        
    final_cols = group_cols + ['Output Case'] + value_cols
    result_df = result_df[final_cols]
    return result_df

# --- ส่วนของหน้าเว็บ Streamlit ---

st.set_page_config(layout="wide")
st.title('โปรแกรมคำนวณ Load Combination 🏗️')

st.write("อัปโหลดไฟล์ `load.csv` ของคุณเพื่อคำนวณ Load Combination")

# <<<<<<<<<<<<<<<<<<<< จุดที่แก้ไข: เพิ่มคำอธิบายก่อนอัปโหลด <<<<<<<<<<<<<<<<<<<<
st.info(
    """
    **ข้อแนะนำ:** ไฟล์ CSV ของคุณควรมีคอลัมน์หลักดังต่อไปนี้เพื่อให้โปรแกรมทำงานได้อย่างถูกต้อง:
    - **`Story`**: ชื่อชั้นของอาคาร
    - **`Column`**: ชื่อเสา
    - **`Unique Name`**: ชื่อเฉพาะขององค์อาคาร
    - **`Station`**: ตำแหน่งบนองค์อาคาร
    - **`Output Case`**: ประเภทของแรง (เช่น Dead, Live, SDL, EX, EY)
    - **`P`, `V2`, `V3`, `T`, `M2`, `M3`**: ค่าแรงในแกนต่างๆ
    """
)
# <<<<<<<<<<<<<<<<<<<< สิ้นสุดจุดที่แก้ไข <<<<<<<<<<<<<<<<<<<<

uploaded_file = st.file_uploader("เลือกไฟล์ load.csv", type=['csv'])

if uploaded_file is not None:
    try:
        input_df = pd.read_csv(uploaded_file)
        st.success("✔️ อัปโหลดไฟล์สำเร็จแล้ว!")
        
        # (ส่วนที่เหลือของโค้ดเหมือนเดิมทั้งหมด)
        if 'main_result_df' not in st.session_state:
            st.session_state.main_result_df = None
        if 'ug_result_df' not in st.session_state:
            st.session_state.ug_result_df = None

        st.subheader("ข้อมูลดิบจากไฟล์ที่อัปโหลด (5 แถวแรก)")
        st.dataframe(input_df.head())

        st.header("1. ผลการคำนวณ Load Combinations (U01 - U09)")
        with st.spinner('กำลังคำนวณ Load Combinations... ⏳'):
            st.session_state.main_result_df = calculate_combinations(input_df.copy())
        
        st.success("✔️ คำนวณเสร็จสิ้น!")

        st.header("2. คำนวณเพิ่มเติมสำหรับชั้นใต้ดิน (Underground Floor)")
        stories = sorted(input_df['Story'].unique())
        base_story = st.selectbox(
            "เลือกชั้นที่จะใช้เป็นฐานในการคำนวณ (จากคอลัมน์ 'Story'):",
            options=stories
        )

        st.write("กรอกตัวคูณ (Factor) ที่ต้องการสำหรับชั้นใต้ดิน:")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            factor_dead_str = st.text_input("Factor for Dead Load", value="1.0")
        with col2:
            factor_sdl_str = st.text_input("Factor for SDL", value="1.0")
        with col3:
            factor_live_str = st.text_input("Factor for Live Load", value="1.0")

        merge_results = st.checkbox("รวมผลลัพธ์ของชั้นใต้ดินกับตารางผลลัพธ์หลัก")

        if st.button("คำนวณชั้นใต้ดิน", type="primary"):
            pattern = re.compile(r"^\d+(\.\d{1,2})?$")
            is_valid = pattern.match(factor_dead_str) and pattern.match(factor_sdl_str) and pattern.match(factor_live_str)

            if is_valid:
                factor_dead = float(factor_dead_str)
                factor_sdl = float(factor_sdl_str)
                factor_live = float(factor_live_str)
                
                with st.spinner('กำลังสร้างข้อมูลชั้นใต้ดิน... ⏳'):
                    base_floor_df = input_df[input_df['Story'] == base_story].copy()
                    value_cols_ug = ['P', 'V2', 'V3', 'T', 'M2', 'M3']
                    factors_map = {'Dead': factor_dead, 'SDL': factor_sdl, 'Live': factor_live}

                    def apply_factors(row):
                        case = row['Output Case']
                        if case in factors_map:
                            row[value_cols_ug] *= factors_map[case]
                        return row

                    ug_df_raw = base_floor_df.apply(apply_factors, axis=1)
                    st.session_state.ug_result_df = calculate_combinations(ug_df_raw, custom_story_name="Underground")
                    st.success("✔️ คำนวณชั้นใต้ดินเสร็จสิ้น!")
            else:
                st.error("🚨 รูปแบบตัวเลขไม่ถูกต้อง! กรุณากรอกเฉพาะตัวเลข และทศนิยมไม่เกิน 2 ตำแหน่ง (เช่น 1.25)")
                st.session_state.ug_result_df = None 
        
        st.divider()
        st.header("3. ผลลัพธ์ทั้งหมด")
        
        final_df_to_display = st.session_state.main_result_df.copy() if st.session_state.main_result_df is not None else None

        if merge_results and st.session_state.ug_result_df is not None:
            final_df_to_display = pd.concat([st.session_state.main_result_df, st.session_state.ug_result_df], ignore_index=True)
            st.info("ตารางแสดงผลลัพธ์หลัก **รวมกับ** ผลลัพธ์ของชั้นใต้ดิน")
            file_name = "load_combinations_combined_result.csv"
        else:
            st.info("ตารางแสดงผลลัพธ์หลัก (หากต้องการรวมชั้นใต้ดิน, กรุณาติ๊ก ✔️ และกดคำนวณ)")
            if st.session_state.ug_result_df is not None:
                st.write("ผลลัพธ์ชั้นใต้ดิน (แยกส่วน)")
                st.dataframe(st.session_state.ug_result_df)
            file_name = "load_combinations_result.csv"

        st.dataframe(final_df_to_display)

        @st.cache_data
        def convert_df_to_csv(df):
            return df.to_csv(index=False).encode('utf-8')
        
        if final_df_to_display is not None:
            csv_output = convert_df_to_csv(final_df_to_display)
            st.download_button(
                label="📥 ดาวน์โหลดผลลัพธ์ทั้งหมดเป็น CSV",
                data=csv_output,
                file_name=file_name,
                mime='text/csv',
            )
            
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")
