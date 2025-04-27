import streamlit as st
import pandas as pd
import datetime
from supabase import create_client, Client

# Supabase Configuration
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_ANON_KEY"]
supabase: Client = create_client(url, key)

# --- Supabase Functions ---

def get_all_projects():
    try:
        response = supabase.table('projects').select('*').execute()
        data = response.data
        if not data:
            st.info("Tidak ada proyek yang ditemukan.")
            return pd.DataFrame()
        df = pd.DataFrame(data)
        df.insert(0, 'No', range(1, len(df) + 1))  # Tambah kolom nomor urut
        return df
    except Exception as e:
        st.error(f"Kesalahan mengambil data proyek: {str(e)}")
        return pd.DataFrame()

def add_project(project_data):
    try:
        supabase.table('projects').insert(project_data).execute()
        st.success("Project berhasil ditambahkan!")
    except Exception as e:
        st.error(f"Gagal menambahkan project: {str(e)}")

def update_project(project_id, updated_data):
    try:
        supabase.table('projects').update(updated_data).eq('id', project_id).execute()
        st.success("Project berhasil diupdate!")
    except Exception as e:
        st.error(f"Gagal mengupdate project: {str(e)}")

def delete_project(project_id):
    try:
        supabase.table('projects').delete().eq('id', project_id).execute()
        st.success("Project berhasil dihapus!")
    except Exception as e:
        st.error(f"Gagal menghapus project: {str(e)}")

def get_all_project_files(project_id):
    try:
        response = supabase.storage.from_("project.files").list(f"project_{project_id}")
        if response.error:
            st.error(f"Error mengambil file: {response.error.message}")
            return pd.DataFrame()
        files = [{"file_name": f["name"], "file_path": f"project_{project_id}/{f['name']}"} for f in response.data]
        return pd.DataFrame(files)
    except Exception as e:
        st.error(f"Error mengambil file: {str(e)}")
        return pd.DataFrame()

def upload_file(project_id, uploaded_file):
    if uploaded_file is not None:
        try:
            file_path = f"project_{project_id}/{uploaded_file.name}"
            res = supabase.storage.from_("project.files").upload(file_path, uploaded_file.getvalue())
            if res.error:
                st.error(f"Gagal upload file: {res.error.message}")
            else:
                st.success("File berhasil diupload!")
        except Exception as e:
            st.error(f"Gagal upload file: {str(e)}")

def delete_file(project_id, file_path):
    try:
        res = supabase.storage.from_("project.files").remove([file_path])
        if res.error:
            st.error(f"Gagal menghapus file: {res.error.message}")
        else:
            st.success("File berhasil dihapus!")
            st.experimental_rerun()
    except Exception as e:
        st.error(f"Gagal menghapus file: {str(e)}")


# --- Streamlit UI ---
st.image("cistech.png", width=450)
st.title("Dashboard Mapping Project TSCM")

tabs = st.tabs(["View Projects", "Add Project", "Edit Project", "Delete Project", "Manage Files"])

with tabs[0]:
    df = get_all_projects()
    if not df.empty:
        display_df = df.rename(columns={
            'project_name': 'Project',
            'category': 'Category',
            'pic': 'PIC',
            'status': 'Status',
            'date_start': 'Start Date',
            'date_end': 'End Date',
            'no_po': 'PO Number'
        })
        # Tampilkan tanpa kolom 'id', pakai 'No' sebagai nomor urut
        display_df = display_df.drop(columns=['id'])
        display_df = display_df.set_index('No')
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No Projects found in the database.")

with tabs[1]:
    st.subheader("Tambah Project Baru")
    with st.form("add_project_form"):
        new_project = st.text_input("Nama Project")
        new_category = st.selectbox("Kategori", ["Project", "Service"])
        new_pic = st.text_input("PIC")
        new_status = st.selectbox("Status", ["Not Started", "Waiting BA", "Not Report", "In Progress", "On Hold", "Completed"])
        new_no_po = st.text_input("Nomor PO")
        today = datetime.date.today()
        start_date, end_date = st.date_input(
            "Pilih Tanggal Mulai dan Selesai",
            value=(today, today + datetime.timedelta(days=30)),
            min_value=today - datetime.timedelta(days=365),
            max_value=today + datetime.timedelta(days=365),
        )
        if st.form_submit_button("Tambah Project"):
            if new_project and new_pic:
                project_data = {
                    'project_name': new_project,
                    'category': new_category,
                    'pic': new_pic,
                    'status': new_status,
                    'date_start': start_date.isoformat(),
                    'date_end': end_date.isoformat(),
                    'no_po': new_no_po
                }
                add_project(project_data)
            else:
                st.error("Nama Project dan PIC wajib diisi!")

with tabs[2]:
    st.subheader("Edit Project")
    df = get_all_projects()
    if df.empty:
        st.info("Tidak ada project yang ditemukan")
    else:
        selected_project = st.selectbox(
            "Pilih Project",
            df['id'].tolist(),
            format_func=lambda x: df[df['id'] == x]['project_name'].iloc[0]
        )
        project_data = df[df['id'] == selected_project].iloc[0]
        with st.form("edit_form"):
            edit_name = st.text_input("Nama Project", value=project_data['project_name'])
            edit_category = st.selectbox("Kategori", ["Project", "Service"], index=0 if project_data['category'] == "Project" else 1)
            edit_pic = st.text_input("PIC", value=project_data['pic'])
            edit_status = st.selectbox(
                "Status",
                ["Not Started", "Waiting BA", "Not Report", "In Progress", "On Hold", "Completed"],
                index=["Not Started", "Waiting BA", "Not Report", "In Progress", "On Hold", "Completed"].index(project_data['status'])
            )
            edit_no_po = st.text_input("Nomor PO", value=project_data['no_po'])
            if st.form_submit_button("Update Project"):
                updated_data = {
                    'project_name': edit_name,
                    'category': edit_category,
                    'pic': edit_pic,
                    'status': edit_status,
                    'no_po': edit_no_po
                }
                update_project(selected_project, updated_data)

with tabs[3]:
    st.subheader("Hapus Project")
    df = get_all_projects()
    if not df.empty:
        selected_project = st.selectbox(
            "Pilih Project untuk Dihapus",
            df['id'].tolist(),
            format_func=lambda x: df[df['id'] == x]['project_name'].iloc[0]
        )
        if st.button("Hapus Project"):
            delete_project(selected_project)

with tabs[4]:
    st.subheader("Kelola File")
    df_projects = get_all_projects()
    if not df_projects.empty:
        selected_project = st.selectbox(
            "Pilih Project",
            df_projects['id'].tolist(),
            format_func=lambda x: df_projects[df_projects['id'] == x]['project_name'].iloc[0],
            key="file_project_select"
        )
        uploaded_file = st.file_uploader("Upload File", type=['pdf', 'docx', 'png', 'jpg', 'jpeg'])
        if uploaded_file is not None:
            if st.button("Upload"):
                upload_file(selected_project, uploaded_file)
                st.experimental_rerun()
        files_df = get_all_project_files(selected_project)
        if not files_df.empty:
            st.write("Daftar File:")
            for index, row in files_df.iterrows():
                col1, col2, col3 = st.columns([4, 2, 1])
                col1.write(row['file_name'])
                url = supabase.storage.from_("project.files").get_public_url(row['file_path'])
                col2.download_button(
                    "Download",
                    data=url,
                    file_name=row['file_name'],
                    key=f"download_{selected_project}_{row['file_name']}_{index}"
                )
                if col3.button("🗑️", key=f"delete_{selected_project}_{row['file_name']}_{index}", on_click=delete_file, args=(selected_project, row['file_path'])):
                    st.experimental_rerun()
        else:
            st.info("Belum ada file di project ini.")
