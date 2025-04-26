import streamlit as st
from PIL import Image
import pandas as pd
import sqlite3
import datetime
import os
from supabase import create_client

# Konfigurasi Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_ANON_KEY"]

supabase = create_client(url,key)

def get_all_projects():
    try:
        response = supabase.table('projects').select('*').execute()
        if response.data:
            df = pd.DataFrame(response.data)
            return df  # Pastikan tipe data kolom sudah sesuai! 
        else:
            st.info("Tidak ada proyek yang ditemukan.")
            return pd.DataFrame() # Return DataFrame kosong jika tidak ada data
    except Exception as e:
        st.error(f"Error fetching projects: {e}")
        return pd.DataFrame()


def add_project(project_data):
    try:
        response = supabase.table('projects').insert(project_data).execute()
        if response.status_code == 201:
            st.success("Proyek berhasil ditambahkan!")
        else:
            st.error(f"Error adding project: {response.error}")

    except Exception as e:
        st.error(f"Error adding project: {e}")


def update_project(project_id, updated_data):
    try:
        response = supabase.table('projects').update(updated_data).eq('id', project_id).execute()
        if response.status_code == 200:
            st.success("Proyek berhasil diperbarui!")
        else:
            st.error(f"Error updating project: {response.error}")

    except Exception as e:
        st.error(f"Error updating project : {e}")


def delete_project(project_id):  # Tambahkan fungsi untuk menghapus proyek di Supabase!

    try: 
      response = supabase.table('projects').delete().eq('id', project_id).execute()
      if response.status_code == 200:
        st.success("Proyek berhasil dihapus!")
      else:
        st.error(f"Error deleting project: {response.error}")
    except Exception as e:
      st.error(f"Error deleting project: {e}")


# --- Streamlit App ---

# ... (rest of your Streamlit app code using the above functions) ...



def get_all_project_files(project_id):
    try:
        with get_connection() as conn:
            df = pd.read_sql(f"SELECT * FROM project_files WHERE project_id = {project_id}", conn)
        return df
    except Exception as e:
        st.error(f"Error fetching project files: {e}")
        return pd.DataFrame()

def upload_file(project_id, uploaded_file):
    if uploaded_file is not None:
        # Simpan file ke Supabase Storage
        file_path = f"project_{project_id}/{uploaded_file.name}"
        response = supabase.storage.from_("project.files").upload(file_path, uploaded_file.getbuffer())
        if response.status_code == 200:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO project_files (project_id, file_name, file_path) VALUES (?, ?, ?)",
                               (project_id, uploaded_file.name, file_path))
                conn.commit()
            st.success("File uploaded successfully!")
        else:
            st.error(f"Error uploading file to Supabase: {response.json()}")

def delete_file(file_id):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM project_files WHERE id=?", (file_id,))
            row = cursor.fetchone()
            if row is not None:
                file_path = row[3]  # Index corrected to 3 for file_path
                response = supabase.storage.from_("project.files").remove([file_path])
                if response.status_code == 204:
                    cursor.execute("DELETE FROM project_files WHERE id=?", (file_id,))
                    conn.commit()
                    st.success("File deleted successfully!")
                else:
                    st.error(f"Error deleting file from Supabase: {response.json()}")
            else:
                st.error("File does not exist.")
    except Exception as e:
        st.error(f"Error deleting file: {e}")

# --- Streamlit App ---
init_db()
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
        }).set_index('id')
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No Projects found in the database.")

with tabs[1]:
    st.subheader("Add New Project")
    with st.form("add_project_form"):
        new_project = st.text_input("Project Name")
        new_category = st.selectbox("Category", ["Project", "Service"])
        new_pic = st.text_input("PIC")
        new_status = st.selectbox("Status", ["Not Started", "Waiting BA", "Not Report", "In Progress", "On Hold", "Completed"])
        new_no_po = st.text_input("PO Number")  # Added PO Number input
        st.write("Select Start and End Dates")
        today = datetime.date.today()
        start_date, end_date = st.date_input(
            "Select start and end dates",
            value=(today, today + datetime.timedelta(days=30)),
            min_value=today - datetime.timedelta(days=365),
            max_value=today + datetime.timedelta(days=365),
        )
        submit_button = st.form_submit_button(label="Add Project")
        if submit_button:
            if new_project and new_pic:
                if isinstance((start_date, end_date), tuple) and len((start_date, end_date)) == 2:
                    add_project(new_project, new_category, new_pic, new_status, start_date, end_date, new_no_po)
                else:
                    st.error("Please select both start and end dates.")
            else:
                st.error("Project Name and PIC are required!")

with tabs[2]:
    st.subheader("Edit Project")
    df = get_all_projects()
    if not df.empty:
        options = df[['id', 'project_name']]
        selected_option = st.selectbox(
            "Choose a Project to Edit",
            options['id'].tolist(),
            format_func=lambda x: options[options['id'] == x]['project_name'].iloc[0]
        )
        selected_row = df[df['id'] == selected_option].iloc[0]
        with st.form("edit_form"):
            edit_project_name = st.text_input("Project Name", selected_row["project_name"])
            edit_category = st.selectbox("Category", ["Project", "Service"], index=["Project", "Service"].index(selected_row['category']))
            edit_pic = st.text_input("PIC", selected_row["pic"])
            edit_status = st.selectbox("Status", ["Not Started", "Waiting BA", "Not Report", "In Progress", "On Hold", "Completed"], index=["Not Started", "Waiting BA", "Not Report", "In Progress", "On Hold", "Completed"].index(selected_row["status"]))
            edit_no_po = st.text_input("PO Number", selected_row["no_po"])  # Added PO Number input
            st.write("Select Start and End Dates")
            start_dt = datetime.datetime.strptime(selected_row['date_start'], '%Y-%m-%d').date()
            end_dt = datetime.datetime.strptime(selected_row['date_end'], '%Y-%m-%d').date()
            start_dt, end_dt = st.date_input(
                "Select start and end dates",
                value=(start_dt, end_dt),
                min_value=datetime.date.today() - datetime.timedelta(days=365),
                max_value=datetime.date.today() + datetime.timedelta(days=365)
            )
            update_btn = st.form_submit_button(label="Update Project")
            if update_btn:
                update_project(selected_option, edit_project_name, edit_category, edit_pic, edit_status, start_dt, end_dt, edit_no_po)

with tabs[3]:
    st.subheader("Delete Project")
    df = get_all_projects()
    if not df.empty:
        delete_options = df[['id', 'project_name']]
        delete_selected_option = st.selectbox(
            "Choose a Project to Delete",
            delete_options['id'].tolist(),
            format_func=lambda x: delete_options[delete_options['id'] == x]['project_name'].iloc[0]
        )
        if st.button("Delete Selected Project"):
            delete_project(delete_selected_option)

with tabs[4]:
    st.subheader("Manage Files for Each Project")

    # Mendapatkan daftar proyek
    df_projects = get_all_projects()

    if not df_projects.empty:
        selected_project = st.selectbox(
            "Choose a Project to Manage Files",
            df_projects['id'].tolist(),
            format_func=lambda x: df_projects[df_projects['id'] == x]['project_name'].iloc[0]
        )

        # Upload file baru
        uploaded_file = st.file_uploader(
            "Upload New File Here",
            type=['pdf', 'docx', 'png', 'jpg', 'jpeg']
        )

        if st.button("Upload New File"):
            upload_file(selected_project, uploaded_file)

        # Mendapatkan daftar file untuk proyek yang dipilih
        files_df = get_all_project_files(selected_project)

        for _, row in files_df.iterrows():
            col1, col2, col3 = st.columns([6, 2, 1])

            # Menampilkan nama file
            col1.write(row['file_name'])

            # Tombol download file
            file_url = supabase.storage.from_("project.files").get_public_url(row['file_path'])
            col2.download_button(
                label="Download",
                data=file_url,
                file_name=row['file_name'],
                mime='application/octet-stream',
                key=f'download-{row.id}'
            )

            # Tombol hapus file
            col3.button(
                label="Clear",
                key=row.id,
                on_click=delete_file,
                args=(row.id,)
            )
