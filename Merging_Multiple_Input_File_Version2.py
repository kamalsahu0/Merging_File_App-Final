<<<<<<< HEAD
#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
import pandas as pd
from io import BytesIO

# Page Configuration
st.set_page_config(page_title="Multi-File Smart Merger", layout="centered")
st.title("Multi-File Merger & Cleaner")

# Initialize Session State
for key in ['file_data', 'sheet_selections', 'merged_df', 'used_files', 'step_number']:
    if key not in st.session_state:
        if key in ['file_data', 'sheet_selections']:
            st.session_state[key] = {}
        elif key == 'merged_df':
            st.session_state[key] = None
        elif key == 'step_number':
            st.session_state[key] = 1
        else:
            st.session_state[key] = set()

# Functions
def load_file(file, sheet_name=None):
    try:
        if file.size == 0:
            raise ValueError("File is empty")

        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            xls = pd.ExcelFile(file)
            sheet = sheet_name or xls.sheet_names[0]
            df = xls.parse(sheet)

        if df.empty:
            raise ValueError("No data found")

        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Failed to load {file.name}: {e}")
        return None

def clean_data(df):
    if df is None:
        st.warning("Skipping cleaning: file could not be loaded.")
        return pd.DataFrame()
    if "Completion %" in df.columns:
        original_shape = df.shape
        df = df.dropna(subset=["Completion %"])
        st.info(f"Cleaned and Removed rows with 'N/A' in completion %: {original_shape[0] - df.shape[0]}")
    return df

def reset_session():
    for key in ['file_data', 'sheet_selections', 'merged_df', 'used_files', 'step_number']:
        if key in st.session_state:
            if key in ['file_data', 'sheet_selections']:
                st.session_state[key] = {}
            elif key == 'merged_df':
                st.session_state[key] = None
            elif key == 'step_number':
                st.session_state[key] = 1
            else:
                st.session_state[key] = set()

def merge_datasets(base_df, new_df, key_base, key_new, join_type='left'):
    try:
        base_df[key_base] = base_df[key_base].astype(str).str.strip()
        new_df[key_new] = new_df[key_new].astype(str).str.strip()

        duplicate_keys = new_df[key_new][new_df[key_new].duplicated()].unique()
        if len(duplicate_keys) > 0:
            st.warning(f"Duplicate keys found in secondary file: {', '.join(duplicate_keys[:10])}")
            return None  # Return None if duplicates found

        overlapping = base_df.columns.intersection(new_df.columns).difference([key_new])
        new_df = new_df.rename(columns={col: f"{col}_1" for col in overlapping})

        new_key_col = key_new
        if key_new in base_df.columns:
            new_key_col = f"{key_new}_1"
            new_df = new_df.rename(columns={key_new: new_key_col})

        merged = pd.merge(base_df, new_df, left_on=key_base, right_on=new_key_col, how=join_type)

        return merged
    except Exception as e:
        st.error(f"Merge failed due to error: {e}")
        return None

def download_csv(df, filename="Merged_Data.csv"):
    buffer = BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    st.download_button("Download Merged CSV", buffer, file_name=filename, mime="text/csv")

# File Upload & Sheet Selector
uploaded_files = st.file_uploader(
    "Upload CSV or Excel files",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True
)

if not uploaded_files:
    reset_session()
    st.info("Upload at least 2 files to begin.")
else:
    uploaded_names = set(file.name for file in uploaded_files)
    existing_names = set(st.session_state.file_data.keys())
    removed_files = existing_names - uploaded_names

    for file in removed_files:
        st.session_state.file_data.pop(file, None)
        st.session_state.sheet_selections.pop(file, None)
        st.session_state.used_files.discard(file)

    for file in uploaded_files:
        with st.container():
            if file.name not in st.session_state.file_data:
                st.session_state.file_data[file.name] = None
                st.session_state.sheet_selections[file.name] = None

            sheet = None
            if file.name.endswith((".xlsx", ".xls")):
                try:
                    xls = pd.ExcelFile(file)
                    sheet_names = xls.sheet_names
                    sheet = st.selectbox(
                        f"Select sheet for {file.name}",
                        sheet_names,
                        key=f"sheet_{file.name}"
                    )
                    st.session_state.sheet_selections[file.name] = sheet
                except Exception as e:
                    st.error(f"Failed to read sheets from {file.name}: {e}")
                    continue

            df = load_file(file, sheet or st.session_state.sheet_selections.get(file.name))
            st.session_state.file_data[file.name] = clean_data(df)

    file_names = list(st.session_state.file_data.keys())

    join_type_map = {
        "Merge all rows (keep all from the Primary file)": "left",
        "Merge only matching rows": "inner"
    }

    join_type = st.selectbox("Select Merge Type", list(join_type_map.keys()))

    if len(file_names) >= 2:
        st.markdown("### Merge Two Files")
        file1 = st.selectbox("Primary File", file_names, key="file1")
        file2 = st.selectbox("Secondary File", [f for f in file_names if f != file1], key="file2")

        key1 = st.selectbox(f"Key in {file1}", st.session_state.file_data[file1].columns, key="key1")
        key2 = st.selectbox(f"Key in {file2}", st.session_state.file_data[file2].columns, key="key2")

        if st.button("Merge Initial Files"):
            merged = merge_datasets(
                st.session_state.file_data[file1],
                st.session_state.file_data[file2],
                key1, key2,
                join_type_map[join_type]
            )
            if merged is not None:
                st.markdown("### Step 1: Merged the first two files...")
                st.session_state.merged_df = merged
                st.session_state.used_files = {file1, file2}
                st.session_state.step_number = 2
            else:
                st.error("Initial merge failed. Please fix errors before proceeding.")

    if st.session_state.merged_df is not None:
        remaining_files = [f for f in file_names if f not in st.session_state.used_files]
        for file in remaining_files:
            with st.expander(f"Merge `{file}`"):
                key_merged = st.selectbox(
                    "Key in merged data",
                    st.session_state.merged_df.columns,
                    key=f"merged_key_{file}"
                )
                key_file = st.selectbox(
                    f"Key in {file}",
                    st.session_state.file_data[file].columns,
                    key=f"file_key_{file}"
                )

                if st.button(f"Merge {file}", key=f"merge_btn_{file}"):
                    merged_result = merge_datasets(
                        st.session_state.merged_df,
                        st.session_state.file_data[file],
                        key_merged,
                        key_file,
                        join_type_map[join_type]
                    )
                    if merged_result is not None:
                        st.markdown(f"### Step {st.session_state.step_number}: Added file: `{file}`")
                        st.session_state.merged_df = merged_result
                        st.session_state.used_files.add(file)
                        st.session_state.step_number += 1
                    else:
                        st.error(f"Merging `{file}` failed. Step not incremented.")

        st.markdown("---")
        st.subheader("Final Merged Output")

        selected_cols = st.multiselect(
            "Select columns to include",
            list(st.session_state.merged_df.columns),
            default=list(st.session_state.merged_df.columns)
        )

        if selected_cols:
            output_df = st.session_state.merged_df[selected_cols]
            st.dataframe(output_df, use_container_width=True)

            filename = st.text_input("Enter output file name", value="merged_output")
            if filename:
                if not filename.endswith(".csv"):
                    filename += ".csv"
                download_csv(output_df, filename)
        else:
            st.warning("Select at least one column to proceed.")

=======
#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
import pandas as pd
from io import BytesIO

# Page Configuration
st.set_page_config(page_title="Multi-File Smart Merger", layout="centered")
st.title("Multi-File Merger & Cleaner")

# Initialize Session State
for key in ['file_data', 'sheet_selections', 'merged_df', 'used_files', 'step_number']:
    if key not in st.session_state:
        if key in ['file_data', 'sheet_selections']:
            st.session_state[key] = {}
        elif key == 'merged_df':
            st.session_state[key] = None
        elif key == 'step_number':
            st.session_state[key] = 1
        else:
            st.session_state[key] = set()

# Functions
def load_file(file, sheet_name=None):
    try:
        if file.size == 0:
            raise ValueError("File is empty")

        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            xls = pd.ExcelFile(file)
            sheet = sheet_name or xls.sheet_names[0]
            df = xls.parse(sheet)

        if df.empty:
            raise ValueError("No data found")

        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Failed to load {file.name}: {e}")
        return None

def clean_data(df):
    if df is None:
        st.warning("Skipping cleaning: file could not be loaded.")
        return pd.DataFrame()
    if "Completion %" in df.columns:
        original_shape = df.shape
        df = df.dropna(subset=["Completion %"])
        st.info(f"Cleaned and Removed rows with 'N/A' in completion %: {original_shape[0] - df.shape[0]}")
    return df

def reset_session():
    for key in ['file_data', 'sheet_selections', 'merged_df', 'used_files', 'step_number']:
        if key in st.session_state:
            if key in ['file_data', 'sheet_selections']:
                st.session_state[key] = {}
            elif key == 'merged_df':
                st.session_state[key] = None
            elif key == 'step_number':
                st.session_state[key] = 1
            else:
                st.session_state[key] = set()

def merge_datasets(base_df, new_df, key_base, key_new, join_type='left'):
    try:
        base_df[key_base] = base_df[key_base].astype(str).str.strip()
        new_df[key_new] = new_df[key_new].astype(str).str.strip()

        duplicate_keys = new_df[key_new][new_df[key_new].duplicated()].unique()
        if len(duplicate_keys) > 0:
            st.warning(f"Duplicate keys found in secondary file: {', '.join(duplicate_keys[:10])}")
            return None  # Return None if duplicates found

        overlapping = base_df.columns.intersection(new_df.columns).difference([key_new])
        new_df = new_df.rename(columns={col: f"{col}_1" for col in overlapping})

        new_key_col = key_new
        if key_new in base_df.columns:
            new_key_col = f"{key_new}_1"
            new_df = new_df.rename(columns={key_new: new_key_col})

        merged = pd.merge(base_df, new_df, left_on=key_base, right_on=new_key_col, how=join_type)

        return merged
    except Exception as e:
        st.error(f"Merge failed due to error: {e}")
        return None

def download_csv(df, filename="Merged_Data.csv"):
    buffer = BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    st.download_button("Download Merged CSV", buffer, file_name=filename, mime="text/csv")

# File Upload & Sheet Selector
uploaded_files = st.file_uploader(
    "Upload CSV or Excel files",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True
)

if not uploaded_files:
    reset_session()
    st.info("Upload at least 2 files to begin.")
else:
    uploaded_names = set(file.name for file in uploaded_files)
    existing_names = set(st.session_state.file_data.keys())
    removed_files = existing_names - uploaded_names

    for file in removed_files:
        st.session_state.file_data.pop(file, None)
        st.session_state.sheet_selections.pop(file, None)
        st.session_state.used_files.discard(file)

    for file in uploaded_files:
        with st.container():
            if file.name not in st.session_state.file_data:
                st.session_state.file_data[file.name] = None
                st.session_state.sheet_selections[file.name] = None

            sheet = None
            if file.name.endswith((".xlsx", ".xls")):
                try:
                    xls = pd.ExcelFile(file)
                    sheet_names = xls.sheet_names
                    sheet = st.selectbox(
                        f"Select sheet for {file.name}",
                        sheet_names,
                        key=f"sheet_{file.name}"
                    )
                    st.session_state.sheet_selections[file.name] = sheet
                except Exception as e:
                    st.error(f"Failed to read sheets from {file.name}: {e}")
                    continue

            df = load_file(file, sheet or st.session_state.sheet_selections.get(file.name))
            st.session_state.file_data[file.name] = clean_data(df)

    file_names = list(st.session_state.file_data.keys())

    join_type_map = {
        "Merge all rows (keep all from the Primary file)": "left",
        "Merge only matching rows": "inner"
    }

    join_type = st.selectbox("Select Merge Type", list(join_type_map.keys()))

    if len(file_names) >= 2:
        st.markdown("### Merge Two Files")
        file1 = st.selectbox("Primary File", file_names, key="file1")
        file2 = st.selectbox("Secondary File", [f for f in file_names if f != file1], key="file2")

        key1 = st.selectbox(f"Key in {file1}", st.session_state.file_data[file1].columns, key="key1")
        key2 = st.selectbox(f"Key in {file2}", st.session_state.file_data[file2].columns, key="key2")

        if st.button("Merge Initial Files"):
            merged = merge_datasets(
                st.session_state.file_data[file1],
                st.session_state.file_data[file2],
                key1, key2,
                join_type_map[join_type]
            )
            if merged is not None:
                st.markdown("### Step 1: Merged the first two files...")
                st.session_state.merged_df = merged
                st.session_state.used_files = {file1, file2}
                st.session_state.step_number = 2
            else:
                st.error("Initial merge failed. Please fix errors before proceeding.")

    if st.session_state.merged_df is not None:
        remaining_files = [f for f in file_names if f not in st.session_state.used_files]
        for file in remaining_files:
            with st.expander(f"Merge `{file}`"):
                key_merged = st.selectbox(
                    "Key in merged data",
                    st.session_state.merged_df.columns,
                    key=f"merged_key_{file}"
                )
                key_file = st.selectbox(
                    f"Key in {file}",
                    st.session_state.file_data[file].columns,
                    key=f"file_key_{file}"
                )

                if st.button(f"Merge {file}", key=f"merge_btn_{file}"):
                    merged_result = merge_datasets(
                        st.session_state.merged_df,
                        st.session_state.file_data[file],
                        key_merged,
                        key_file,
                        join_type_map[join_type]
                    )
                    if merged_result is not None:
                        st.markdown(f"### Step {st.session_state.step_number}: Added file: `{file}`")
                        st.session_state.merged_df = merged_result
                        st.session_state.used_files.add(file)
                        st.session_state.step_number += 1
                    else:
                        st.error(f"Merging `{file}` failed. Step not incremented.")

        st.markdown("---")
        st.subheader("Final Merged Output")

        selected_cols = st.multiselect(
            "Select columns to include",
            list(st.session_state.merged_df.columns),
            default=list(st.session_state.merged_df.columns)
        )

        if selected_cols:
            output_df = st.session_state.merged_df[selected_cols]
            st.dataframe(output_df, use_container_width=True)

            filename = st.text_input("Enter output file name", value="merged_output")
            if filename:
                if not filename.endswith(".csv"):
                    filename += ".csv"
                download_csv(output_df, filename)
        else:
            st.warning("Select at least one column to proceed.")

>>>>>>> a90a673 (Increase limit to 2gb)
