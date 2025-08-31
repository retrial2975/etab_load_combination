import streamlit as st
import pandas as pd
import numpy as np
import re

# --- ส่วนของการคำนวณ (โหมด Column และ Wall) ---
def calculate_combinations(df_input, custom_story_name=None, mode='Column'):
    df = df_input.copy()
    # สำหรับโหมด Column/Wall จะใช้ P, V2, V3, ...
    value_cols = ['P', 'V2', 'V3', 'T', 'M2', 'M3']
    
    if mode == 'Column':
        group_cols = ['Story', 'Column', 'Unique Name', 'Station']
    else: # Wall
        group_cols = ['Story', 'Pier', 'Location']
    
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
            
            # เงื่อนไขพิเศษสำหรับ V2, V3
            if val_col in ['V2', 'V3']:
                f_ex *= 2.5; f_ey *= 2.5
            
            total_val = (p_dead * f_dead) + (p_sdl * f_sdl) + (p_live * f_live) + (p_ex * f_ex) + (p_ey * f_ey)
            temp_df[val_col] = total_val
        combo_dfs[name] = temp_df

    result_df = pd.concat(combo_dfs.values(), ignore_index=True)
    result_df[value_cols] = result_df[value_cols].round(4)
    final_cols = group_cols + ['Output Case'] + value_cols
    return result_df[final_cols]

# --- <<<<<<<<<<<<<<<<<<<< ฟังก์ชันใหม่สำหรับ Mode Reaction <<<<<<<<<<<<<<<<<<<< ---
def calculate_reaction_combinations(df_load, df_coords, pre_combo_factors):
    df = df_load.copy()
    
    # สำหรับโหมด Reaction จะใช้ FX, FY, FZ, ...
    value_cols = ['FX', 'FY', 'FZ', 'MX', 'MY', 'MZ']
    group_cols = ['Story', 'Unique Name']

    # --- ขั้นตอนที่ 1: คูณค่าด้วย Factor ที่ผู้ใช้กรอกเข้ามาก่อน ---
    factor_cols = ['FZ', 'MX', 'MY', 'MZ']
    for case, factor in pre_combo_factors.items():
        if factor != 1.0: # ทำเฉพาะเมื่อ factor ไม่ใช่ 1 เพื่อประสิทธิภาพ
            mask = df['Output Case'] == case
            df.loc[mask, factor_cols] = df.loc[mask, factor_cols] * factor

    # --- ขั้นตอนที่ 2: Pivot Table ---
    pivot_df = df.pivot_table(index=group_cols, columns='Output Case', values=value_cols, fill_value=0)
    pivot_df.columns = ['_'.join(map(str, col)).strip() for col in pivot_df.columns.values]
    pivot_df.reset_index(inplace=True)

    required_cases = ['Dead', 'SDL', 'Live', 'EX', 'EY']
    for case in required_cases:
        for val in value_cols:
            col_name = f'{val}_{case}'
            if col_name not in pivot_df.columns:
                pivot_df[col_name] = 0

    # --- ขั้นตอนที่ 3: คำนวณ Load Combinations ---
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
            v_dead = pivot_df.get(f'{val_col}_Dead', pd.Series(0, index=pivot_df.index))
            v_sdl = pivot_df.get(f'{val_col}_SDL', pd.Series(0, index=pivot_df.index))
            v_live = pivot_df.get(f'{val_col}_Live', pd.Series(0, index=pivot_df.index))
            v_ex = pivot_df.get(f'{val_col}_EX', pd.Series(0, index=pivot_df.index))
            v_ey = pivot_df.get(f'{val_col}_EY', pd.Series(0, index=pivot_df.index))
            
            f_dead = factors.get('Dead', 0); f_sdl = factors.get('SDL', 0); f_live = factors.get('Live', 0)
            f_ex = factors.get('EX', 0); f_ey = factors.get('EY', 0)
            
            # --- เงื่อนไขพิเศษสำหรับ FX, FY ---
            if val_col in ['FX', 'FY']:
                f_ex *= 2.5; f_ey *= 2.5
            
            total_val = (v_dead * f_dead) + (v_sdl * f_sdl) + (v_live * f_live) + (v_ex * f_ex) + (v_ey * f_ey)
            temp_df[val_col] = total_val
        combo_dfs[name] = temp_df

    result_df = pd.concat(combo_dfs.values(), ignore_index=True)

    # --- ขั้นตอนที่ 4: รวมผลลัพธ์กับไฟล์พิกัด ---
    df_coords.rename(columns={'UniqueName': 'Unique Name'}, inplace=True, errors='ignore')
    coords_to_merge = df_coords[['Unique Name', 'X', 'Y', 'Z']].drop_duplicates(subset=['Unique Name'])
    
    final_df = pd.merge(result_df, coords_to_merge, on='Unique Name', how='left')

    # --- ขั้นตอนที่ 5: จัดเรียงและจัดรูปแบบผลลัพธ์ ---
    final_df[value_cols] = final_df[value_cols].round(4)
    # จัดเรียงคอลัมน์ใหม่เพื่อให้ดูง่าย
    final_cols = ['Story', 'Unique Name', 'X', 'Y', 'Z', 'Output Case'] + value_cols
    return final_df[final_cols]
# --- <<<<<<<<<<<<<<<<<<<< สิ้นสุดฟังก์ชันใหม่ <<<<<<<<<<<<<<<<<<<< ---


# --- ส่วนของหน้าเว็บ Streamlit ---
st.set_page_config(layout="wide")
st.title('โปรแกรมคำนวณ Load Combination 🏗️')

# <<<<<<<<<<<<<<<<<<<< จุดที่แก้ไข: เพิ่มปุ่มเลือก Mode 'Reaction' <<<<<<<<<<<<<<<<<<<<
mode = st.radio(
    "เลือกโหมดการคำนวณ:",
    ('Column', 'Wall', 'Reaction'), # เพิ่ม Reaction
    horizontal=True,
    help="เลือก 'Column' หรือ 'Wall' สำหรับการคำนวณแรงในชิ้นส่วน | เลือก 'Reaction' สำหรับการคำนวณแรงปฏิกิริยาที่ฐานราก"
)
st.divider()

# --- โหมด Column และ Wall (โค้ดเดิม) ---
if mode in ['Column', 'Wall']:
    st.header(f"โหมดการคำนวณ: {mode}")
    st.write("อัปโหลดไฟล์ CSV ของคุณเพื่อคำนวณ Load Combination")

    if mode == 'Column':
        st.info(
            """
            **โหมด Column:** ไฟล์ CSV ของคุณควรมีคอลัมน์หลักดังต่อไปนี้:
            - **`Story`**, **`Column`**, **`Unique Name`**, **`Station`**
            - **`Output Case`** (ต้องมีค่า: Dead, Live, SDL, EX, EY เป็นอย่างน้อย)
            - **`P`**, **`V2`**, **`V3`**, **`T`**, **`M2`**, **`M3`**
            """
        )
        required_cols = {'Story', 'Column', 'Unique Name', 'Station', 'Output Case', 'P', 'V2', 'V3', 'T', 'M2', 'M3'}
    else: # Wall Mode
        st.info(
            """
            **โหมด Wall:** ไฟล์ CSV ของคุณควรมีคอลัมน์หลักดังต่อไปนี้:
            - **`Story`**, **`Pier`**, **`Location`**
            - **`Output Case`** (ต้องมีค่า: Dead, Live, SDL, EX, EY เป็นอย่างน้อย)
            - **`P`**, **`V2`**, **`V3`**, **`T`**, **`M2`**, **`M3`**
            """
        )
        required_cols = {'Story', 'Pier', 'Location', 'Output Case', 'P', 'V2', 'V3', 'T', 'M2', 'M3'}

    uploaded_file = st.file_uploader(f"เลือกไฟล์สำหรับโหมด {mode}", type=['csv'])

    if uploaded_file is not None:
        try:
            input_df = pd.read_csv(uploaded_file)
            
            if not required_cols.issubset(input_df.columns):
                missing_cols = required_cols - set(input_df.columns)
                st.error(f"🚨 ไฟล์ของคุณขาดคอลัมน์ที่จำเป็นสำหรับโหมด {mode}: **{', '.join(missing_cols)}**")
                st.stop()

            input_df['Output Case'] = input_df['Output Case'].str.strip()
            allowed_cases = ['Dead', 'Live', 'SDL', 'EX', 'EY']
            input_df = input_df[input_df['Output Case'].isin(allowed_cases)]
            st.success("✔️ อัปโหลดไฟล์สำเร็จแล้ว!")
            
            st.subheader("ตรวจสอบไฟล์เบื้องต้น")
            required_oc_cases = {'Dead', 'Live', 'SDL', 'EX', 'EY'}
            uploaded_cases = set(input_df['Output Case'].unique())
            missing_oc_cases = required_oc_cases - uploaded_cases
            
            if not missing_oc_cases:
                st.success("✔️ พบ Output Case ที่จำเป็นครบถ้วน")
                can_proceed = True
            else:
                st.error(f"🚨 พบว่าขาด Output Case ที่จำเป็น: **{', '.join(sorted(list(missing_oc_cases)))}**")
                st.warning("กรุณาตรวจสอบไฟล์ CSV ของคุณและอัปโหลดใหม่อีกครั้ง")
                can_proceed = False

            if can_proceed:
                if 'main_result_df' not in st.session_state:
                    st.session_state.main_result_df, st.session_state.ug_result_df = None, None

                st.subheader("ข้อมูลดิบจากไฟล์ที่อัปโหลด (หลังกรองแล้ว)")
                st.dataframe(input_df.head())
                st.header("1. ผลการคำนวณ Load Combinations")
                with st.expander("แสดง/ซ่อนสูตรที่ใช้คำนวณ"):
                    st.markdown("""
                    - **U01**: `1.4*Dead + 1.4*SDL + 1.7*Live`
                    - **U02**: `1.05*Dead + 1.05*SDL + 1.275*Live + EX`
                    - ... (และสูตรอื่นๆ)
                    - **หมายเหตุ:** สำหรับค่า `V2` และ `V3` เทอม `EX` และ `EY` จะถูกคูณด้วย **2.5**
                    """)
                
                with st.spinner('กำลังคำนวณ Load Combinations... ⏳'):
                    st.session_state.main_result_df = calculate_combinations(input_df, mode=mode)
                st.success("✔️ คำนวณเสร็จสิ้น!")

                # --- (ส่วนของ Underground Floor เหมือนเดิม) ---
                st.header("2. คำนวณเพิ่มเติมสำหรับชั้นใต้ดิน (Underground Floor)")
                # ... (โค้ดส่วนนี้เหมือนเดิมทั้งหมด) ...
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
                            st.session_state.ug_result_df = calculate_combinations(ug_df_raw, custom_story_name="Underground", mode=mode)
                            st.success("✔️ คำนวณชั้นใต้ดินเสร็จสิ้น!")
                    else:
                        st.error("🚨 รูปแบบตัวเลขไม่ถูกต้อง!")
                        st.session_state.ug_result_df = None
                
                st.divider()
                st.header("3. ผลลัพธ์ทั้งหมด")
                # ... (ส่วนแสดงผลและดาวน์โหลดเหมือนเดิม) ...
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

# --- <<<<<<<<<<<<<<<<<<<< โค้ดใหม่สำหรับ Mode Reaction <<<<<<<<<<<<<<<<<<<< ---
else: # mode == 'Reaction'
    st.header("โหมด Reaction: คำนวณ Combination จากแรงปฏิกิริยาที่ฐาน")
    st.info(
        """
        **คำแนะนำ:** โปรดอัปโหลด 2 ไฟล์ตามลำดับ:
        1.  **ไฟล์ Load:** ควรมีคอลัมน์: `Story`, `Unique Name`, `Output Case`, `FX`, `FY`, `FZ`, `MX`, `MY`, `MZ`
        2.  **ไฟล์พิกัด:** ควรมีคอลัมน์: `UniqueName`, `X`, `Y`, `Z`
        """
    )
    
    col1, col2 = st.columns(2)
    with col1:
        uploaded_load_file = st.file_uploader("1. อัปโหลดไฟล์ Load", type=['csv'], key="reaction_load")
    with col2:
        uploaded_coord_file = st.file_uploader("2. อัปโหลดไฟล์พิกัด", type=['csv'], key="reaction_xy")

    if uploaded_load_file is not None and uploaded_coord_file is not None:
        try:
            df_load = pd.read_csv(uploaded_load_file)
            df_coords = pd.read_csv(uploaded_coord_file)

            required_load_cols = {'Story', 'Unique Name', 'Output Case', 'FX', 'FY', 'FZ', 'MX', 'MY', 'MZ'}
            required_coord_cols = {'UniqueName', 'X', 'Y', 'Z'}

            if not required_load_cols.issubset(df_load.columns):
                missing = required_load_cols - set(df_load.columns)
                st.error(f"🚨 ไฟล์ Load ขาดคอลัมน์: **{', '.join(missing)}**")
                st.stop()
            
            if not required_coord_cols.issubset(df_coords.columns):
                missing = required_coord_cols - set(df_coords.columns)
                st.error(f"🚨 ไฟล์พิกัดขาดคอลัมน์: **{', '.join(missing)}**")
                st.stop()

            df_load['Output Case'] = df_load['Output Case'].str.strip()
            allowed_cases = ['Dead', 'Live', 'SDL', 'EX', 'EY']
            df_load_filtered = df_load[df_load['Output Case'].isin(allowed_cases)].copy()
            st.success("✔️ อัปโหลดไฟล์ทั้ง 2 สำเร็จ!")

            required_oc_cases = {'Dead', 'Live', 'SDL', 'EX', 'EY'}
            uploaded_cases = set(df_load_filtered['Output Case'].unique())
            missing_oc_cases = required_oc_cases - uploaded_cases
            if missing_oc_cases:
                st.error(f"🚨 ไฟล์ Load ขาด Output Case ที่จำเป็น: **{', '.join(sorted(list(missing_oc_cases)))}**")
                st.stop()
            else:
                st.success("✔️ พบ Output Case ที่จำเป็นครบถ้วน")
            
            st.subheader("ข้อมูลดิบ (ตัวอย่าง 5 แถวแรก)")
            st.write("ไฟล์ Load (หลังกรองแล้ว):")
            st.dataframe(df_load_filtered.head())
            st.write("ไฟล์พิกัด:")
            st.dataframe(df_coords.head())

            st.divider()
            
            st.subheader("1. กำหนดตัวคูณ (Factor) สำหรับค่าแรงก่อนคำนวณ Combination")
            st.write("ค่า Factor เหล่านี้จะถูกนำไปคูณกับค่า **FZ, MX, MY, MZ** ของแต่ละ Load Case ก่อนนำไปรวมในสูตร U01-U09")
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1: factor_dead_str = st.text_input("Factor for Dead Load", "1.0", key="f_dead_r")
            with f_col2: factor_sdl_str = st.text_input("Factor for SDL", "1.0", key="f_sdl_r")
            with f_col3: factor_live_str = st.text_input("Factor for Live Load", "1.0", key="f_live_r")
            
            st.divider()
            
            if st.button("คำนวณ Reaction Combination", type="primary"):
                pattern = re.compile(r"^\d+(\.\d+)?$")
                if all(pattern.match(s) for s in [factor_dead_str, factor_sdl_str, factor_live_str]):
                    factors = {
                        'Dead': float(factor_dead_str),
                        'SDL': float(factor_sdl_str),
                        'Live': float(factor_live_str)
                    }
                    
                    with st.spinner('กำลังคำนวณ... ⏳'):
                        result_df = calculate_reaction_combinations(df_load_filtered, df_coords, factors)
                        st.session_state.reaction_result_df = result_df

                    st.success("✔️ คำนวณเสร็จสิ้น!")
                    st.header("2. ผลลัพธ์การคำนวณ")
                    st.dataframe(st.session_state.reaction_result_df)
                    
                    @st.cache_data
                    def convert_df_to_csv_reaction(df): return df.to_csv(index=False).encode('utf-8')
                    
                    st.download_button(
                        "📥 ดาวน์โหลดผลลัพธ์เป็น CSV",
                        convert_df_to_csv_reaction(st.session_state.reaction_result_df),
                        "reaction_combinations_result.csv",
                        'text/csv'
                    )
                else:
                    st.error("🚨 รูปแบบตัวเลข Factor ไม่ถูกต้อง! กรุณาใส่เป็นตัวเลข เช่น 1.0, 0.95")

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")
