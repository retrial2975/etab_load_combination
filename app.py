import streamlit as st
import pandas as pd
import numpy as np
import re # <-- นำเข้า Library สำหรับ Regular Expression

# --- ส่วนของการคำนวณ ---
# (ฟังก์ชัน calculate_combinations เหมือนเดิมทุกประการ)
def calculate_combinations(df, custom_story_name=None):
    """
    ฟังก์ชันสำหรับคำนวณ Load Combination จาก DataFrame ที่รับเข้ามา
    - df: DataFrame ข้อมูลดิบ
    - custom_story_name: ชื่อ Story ที่จะใช้สำหรับผลลัพธ์ (กรณีชั้นใต้ดิน)
    """
    value_cols = ['P', 'V2', 'V3', 'T', 'M2', 'M3']
    group_cols = ['Story', 'Column', 'Unique Name', 'Station']
    
    if custom_story_name:
        df['Original_Story_for_UG'] = df['Story']
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

uploaded_file = st.file_uploader("เลือกไฟล์ load.csv", type=['csv'])

if uploaded_file is not None:
    try:
        input_df = pd.read_csv(uploaded_file)
        st.success("✔️ อัปโหลดไฟล์สำเร็จแล้ว!")

        st.subheader("ข้อมูลดิบจากไฟล์ที่อัปโหลด (5 แถวแรก)")
        st.dataframe(input_df.head())

        # ... (โค้ดส่วนคำนวณหลักเหมือนเดิม) ...
        st.header("1. ผลการคำนวณ Load Combinations (U01 - U09)")
        with st.expander("แสดง/ซ่อนสูตรที่ใช้คำนวณ"):
             st.markdown("""...""") 

        with st.spinner('กำลังคำนวณ Load Combinations... ⏳'):
            main_result_df = calculate_combinations(input_df.copy())
        
        st.success("✔️ คำนวณเสร็จสิ้น!")
        st.dataframe(main_result_df)

        @st.cache_data
        def convert_df_to_csv(df):
            return df.to_csv(index=False).encode('utf-8')

        csv_main_output = convert_df_to_csv(main_result_df)
        st.download_button(
            label="📥 ดาวน์โหลดผลลัพธ์หลักเป็น CSV",
            data=csv_main_output,
            file_name='load_combinations_result.csv',
            mime='text/csv',
        )
        st.divider()

        # --- ส่วนคำนวณชั้นใต้ดิน ---
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

        if st.button("คำนวณชั้นใต้ดิน", type="primary"):
            # <<<<<<<<<<<<<<<<<<<< จุดที่แก้ไข <<<<<<<<<<<<<<<<<<<<
            # 1. กำหนดรูปแบบที่ถูกต้อง: ตัวเลขอย่างน้อย 1 ตัว และทศนิยมไม่เกิน 2 ตำแหน่ง (ถ้ามี)
            pattern = re.compile(r"^\d+(\.\d{1,2})?$")

            # 2. ตรวจสอบแต่ละช่องกรอก
            is_dead_valid = pattern.match(factor_dead_str)
            is_sdl_valid = pattern.match(factor_sdl_str)
            is_live_valid = pattern.match(factor_live_str)

            # 3. ถ้าทุกช่องถูกต้อง ให้ทำงานต่อ, ถ้าไม่ ให้แสดง Error
            if is_dead_valid and is_sdl_valid and is_live_valid:
                try:
                    factor_dead = float(factor_dead_str)
                    factor_sdl = float(factor_sdl_str)
                    factor_live = float(factor_live_str)

                    # ... (ส่วนการคำนวณที่เหลือเหมือนเดิม) ...
                    with st.spinner('กำลังสร้างข้อมูลชั้นใต้ดิน... ⏳'):
                        base_floor_df = input_df[input_df['Story'] == base_story].copy()
                        
                        value_cols_ug = ['P', 'V2', 'V3', 'T', 'M2', 'M3']
                        
                        factors_map = {
                            'Dead': factor_dead, 'SDL': factor_sdl, 'Live': factor_live
                        }

                        def apply_factors(row):
                            case = row['Output Case']
                            if case in factors_map:
                                row[value_cols_ug] *= factors_map[case]
                            return row

                        ug_df_raw = base_floor_df.apply(apply_factors, axis=1)

                        st.subheader("ผลลัพธ์ Load Combinations สำหรับชั้นใต้ดิน")
                        st.write(f"คำนวณโดยใช้ชั้น `{base_story}` เป็นฐาน และเปลี่ยนชื่อ Story เป็น `Underground`")
                        
                        ug_result_df = calculate_combinations(ug_df_raw, custom_story_name="Underground")
                        st.dataframe(ug_result_df)

                        csv_ug_output = convert_df_to_csv(ug_result_df)
                        st.download_button(
                            label="📥 ดาวน์โหลดผลลัพธ์ชั้นใต้ดินเป็น CSV",
                            data=csv_ug_output,
                            file_name=f'underground_combinations_from_{base_story.replace(" ", "_")}.csv',
                            mime='text/csv',
                            key='download_ug'
                        )
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
            else:
                st.error("🚨 รูปแบบตัวเลขไม่ถูกต้อง! กรุณากรอกเฉพาะตัวเลข และทศนิยมไม่เกิน 2 ตำแหน่ง (เช่น 1.25)")
            # <<<<<<<<<<<<<<<<<<<< สิ้นสุดจุดที่แก้ไข <<<<<<<<<<<<<<<<<<<<

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")
