import streamlit as st
import pandas as pd
import numpy as np
import re

# --- ส่วนของการคำนวณ ---
# (ฟังก์ชัน calculate_combinations เหมือนเดิมทุกประการ)
def calculate_combinations(df_input, custom_story_name=None):
    df = df_input.copy()
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
        'U01': {'Dead': 1.4, 'SDL': 1.4, 'Live': 1.7}, 'U02': {'Dead': 1.05, 'SDL': 1.05, 'Live': 1.275, 'EX': 1},
        'U03': {'Dead': 1.05, 'SDL': 1.05, 'Live': 1.275, 'EX': -1}, 'U04': {'Dead': 1.05, 'SDL': 1.05, 'Live': 1.275, 'EY': 1},
        'U05': {'Dead': 1.05, 'SDL': 1.05, 'Live': 1.275, 'EY': -1}, 'U06': {'Dead': 0.9, 'SDL': 0.9, 'EX': 1},
        'U07': {'Dead': 0.9, 'SDL': 0.9, 'EX': -1}, 'U08': {'Dead': 0.9, 'SDL': 0.9, 'EY': 1},
        'U09': {'Dead': 0.9, 'SDL': 0.9, 'EY': -1},
    }

    for name, factors in combinations.items():
        formula_parts = []
        ordered_cases = ['Dead', 'SDL', 'Live', 'EX', 'EY']
        for case in ordered_cases:
            factor_val = factors.get(case)
            if factor_val:
                formula_parts.append(f"{factor_val:+g}{case}")
        formula_string = "".join(formula_parts).lstrip('+')
        full_formula_name = f"{name}: {formula_string}"
        
        temp_df = pivot_df[group_cols].copy()
        temp_df['Output Case'] = full_formula_name
        
        for val_col in value_cols:
            p_dead = pivot_df.get(f'{val_col}_Dead', pd.Series(0, index=pivot_df.index))
            p_sdl = pivot_df.get(f'{val_col}_SDL', pd.Series(0, index=pivot_df.index))
            p_live = pivot_df.get(f'{val_col}_Live', pd.Series(0, index=pivot_df.index))
            p_ex = pivot_df.get(f'{val_col}_EX', pd.Series(0, index=pivot_df.index))
            p_ey = pivot_df.get(f'{val_col}_EY', pd.Series(0, index=pivot_df.index))
            
            f_dead = factors.get('Dead', 0); f_sdl = factors.get('SDL', 0); f_live = factors.get('Live', 0)
            f_ex = factors.get('EX', 0); f_ey = factors.get('EY', 0)
            
            if val_col in ['V2', 'V3']:
                f_ex *= 2.5; f_ey *= 2.5
            
            total_val = (p_dead * f_dead) + (p_sdl * f_sdl) + (p_live * f_live) + (p_ex * f_ex) + (p_ey * f_ey)
            temp_df[val_col] = total_val
        combo_dfs[name] = temp_df

    result_df = pd.concat(combo_dfs.values(), ignore_index=True)
    result_df[value_cols] = result_df[value_cols].round(4)
    final_cols = group_cols + ['Output Case'] + value_cols
    return result_df[final_cols]

# --- ส่วนของหน้าเว็บ Streamlit ---
st.set_page_config(layout="wide")
st.title('โปรแกรมคำนวณ Load Combination 🏗️')
st.write("อัปโหลดไฟล์ `load.csv` ของคุณเพื่อคำนวณ Load Combination")
st.info(
    """
    **ข้อแนะนำ:** ไฟล์ CSV ของคุณควรมีคอลัมน์หลักดังต่อไปนี้:
    - **`Story`**, **`Column`**, **`Unique Name`**, **`Station`**
    - **`Output Case`** (ต้องมีค่า: Dead, Live, SDL, EX, EY เป็นอย่างน้อย)
    - **`P`**, **`V2`**, **`V3`**, **`T`**, **`M2`**, **`M3`**
    """
)
uploaded_file = st.file_uploader("เลือกไฟล์ load.csv", type=['csv'])

if uploaded_file is not None:
    try:
        input_df = pd.read_csv(uploaded_file)
        
        if 'Output Case' not in input_df.columns:
            st.error("🚨 ไม่พบคอลัมน์ 'Output Case' ในไฟล์ที่อัปโหลด!")
            st.stop()
        
        # 1. ทำความสะอาดข้อมูล 'Output Case'
        input_df['Output Case'] = input_df['Output Case'].str.strip()
        
        # <<<<<<<<<<<<<<<<<<<< จุดที่แก้ไข: กรองเอาเฉพาะ Output Case ที่ต้องการ <<<<<<<<<<<<<<<<<<<<
        allowed_cases = ['Dead', 'Live', 'SDL', 'EX', 'EY']
        input_df = input_df[input_df['Output Case'].isin(allowed_cases)]
        # <<<<<<<<<<<<<<<<<<<< สิ้นสุดจุดที่แก้ไข <<<<<<<<<<<<<<<<<<<<
        
        st.success("✔️ อัปโหลดไฟล์สำเร็จแล้ว!")
        
        # 2. ตรวจสอบว่า Case ที่จำเป็นมีครบหรือไม่
        st.subheader("ตรวจสอบไฟล์เบื้องต้น")
        required_cases = {'Dead', 'Live', 'SDL', 'EX', 'EY'}
        uploaded_cases = set(input_df['Output Case'].unique())
        missing_cases = required_cases - uploaded_cases
        
        if not missing_cases:
            st.success("✔️ พบ Output Case ที่จำเป็นครบถ้วน")
            can_proceed = True
        else:
            st.error(f"🚨 พบว่าขาด Output Case ที่จำเป็น: **{', '.join(sorted(list(missing_cases)))}**")
            st.warning("กรุณาตรวจสอบไฟล์ CSV ของคุณและอัปโหลดใหม่อีกครั้ง")
            can_proceed = False

        if can_proceed:
            # ... (ส่วนที่เหลือของโค้ดเหมือนเดิมทุกประการ) ...
            if 'main_result_df' not in st.session_state:
                st.session_state.main_result_df, st.session_state.ug_result_df = None, None

            st.subheader("ข้อมูลดิบจากไฟล์ที่อัปโหลด (หลังกรองแล้ว)")
            st.dataframe(input_df.head())
            st.header("1. ผลการคำนวณ Load Combinations")
            with st.expander("แสดง/ซ่อนสูตรที่ใช้คำนวณ"):
                st.markdown("""
                - **U01**: `1.4*Dead + 1.4*SDL + 1.7*Live`
                # ... (เนื้อหาสูตรอื่นๆ เหมือนเดิม) ...
                """)
            with st.spinner('กำลังคำนวณ Load Combinations... ⏳'):
                st.session_state.main_result_df = calculate_combinations(input_df)
            st.success("✔️ คำนวณเสร็จสิ้น!")

            st.header("2. คำนวณเพิ่มเติมสำหรับชั้นใต้ดิน (Underground Floor)")
            stories = sorted(input_df['Story'].unique())
            base_story = st.selectbox("เลือกชั้นที่จะใช้เป็นฐานในการคำนวณ:", options=stories)
            st.write("กรอกตัวคูณ (Factor) ที่ต้องการสำหรับชั้นใต้ดิน:")
            col1, col2, col3 = st.columns(3)
            with col1: factor_dead_str = st.text_input("Factor for Dead Load", "1.0")
            with col2: factor_sdl_str = st.text_input("Factor for SDL", "1.0")
            with col3: factor_live_str = st.text_input("Factor for Live Load", "1.0")
            merge_results = st.checkbox("รวมผลลัพธ์ของชั้นใต้ดินกับตารางผลลัพธ์หลัก")
            if st.button("คำนวณชั้นใต้ดิน", type="primary"):
                pattern = re.compile(r"^\d+(\.\d{1,2})?$")
                if all(pattern.match(s) for s in [factor_dead_str, factor_sdl_str, factor_live_str]):
                    factor_dead, factor_sdl, factor_live = map(float, [factor_dead_str, factor_sdl_str, factor_live_str])
                    with st.spinner('กำลังสร้างข้อมูลชั้นใต้ดิน... ⏳'):
                        base_floor_df = input_df[input_df['Story'] == base_story].copy()
                        value_cols_ug = ['P', 'V2', 'V3', 'T', 'M2', 'M3']
                        factors_map = {'Dead': factor_dead, 'SDL': factor_sdl, 'Live': factor_live}
                        dfs_to_combine = []
                        unmodified_mask = ~base_floor_df['Output Case'].isin(factors_map.keys())
                        dfs_to_combine.append(base_floor_df[unmodified_mask])
                        for case, factor in factors_map.items():
                            mask = base_floor_df['Output Case'] == case
                            if mask.any():
                                modified_part = base_floor_df[mask].copy()
                                modified_part[value_cols_ug] *= factor
                                dfs_to_combine.append(modified_part)
                        ug_df_raw = pd.concat(dfs_to_combine).reset_index(drop=True)
                        st.session_state.ug_result_df = calculate_combinations(ug_df_raw, custom_story_name="Underground")
                        st.success("✔️ คำนวณชั้นใต้ดินเสร็จสิ้น!")
                else:
                    st.error("🚨 รูปแบบตัวเลขไม่ถูกต้อง!")
                    st.session_state.ug_result_df = None
            st.divider()
            st.header("3. ผลลัพธ์ทั้งหมด")
            final_df = st.session_state.main_result_df.copy() if st.session_state.main_result_df is not None else None
            if merge_results and st.session_state.ug_result_df is not None:
                final_df = pd.concat([st.session_state.main_result_df, st.session_state.ug_result_df], ignore_index=True)
                st.info("ตารางแสดงผลลัพธ์หลัก **รวมกับ** ผลลัพธ์ของชั้นใต้ดิน")
                file_name = "load_combinations_combined_result.csv"
            else:
                st.info("ตารางแสดงผลลัพธ์หลัก (หากต้องการรวมชั้นใต้ดิน, กรุณาติ๊ก ✔️ และกดคำนวณ)")
                if st.session_state.ug_result_df is not None:
                    st.write("ผลลัพธ์ชั้นใต้ดิน (แยกส่วน)")
                    st.dataframe(st.session_state.ug_result_df)
                file_name = "load_combinations_result.csv"
            st.dataframe(final_df)
            @st.cache_data
            def convert_df_to_csv(df): return df.to_csv(index=False).encode('utf-8')
            if final_df is not None:
                st.download_button("📥 ดาวน์โหลดผลลัพธ์ทั้งหมดเป็น CSV", convert_df_to_csv(final_df), file_name, 'text/csv')
                
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")
