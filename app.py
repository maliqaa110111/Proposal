import streamlit as st
from PIL import Image
import pandas as pd
import sqlite3
import datetime
import os
from supabase import create_client

# Supabase Configuration
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(url, key)

def get_all_projects():
    try:
        response = supabase.table('projects').select('*').execute()
        print(response.json()) # Untuk debugging, lihat isi response

        if response.error:
            st.error(f"Kesalahan mengambil data proyek: {response.error.message}")
            return pd.DataFrame() # Mengembalikan DataFrame kosong jika ada error

        if response.data is None or len(response.data) == 0: #cek jika datanya kosong
            st.info("Tidak ada proyek yang ditemukan.")
            return pd.DataFrame() # Mengembalikan DataFrame kosong jika tidak ada data

        df = pd.DataFrame(response.data)
        return df
    except Exception as e:
        st.error(f"Kesalahan tak terduga: {e}")
        return pd.DataFrame() # Mengembalikan DataFrame kosong jika ada exception



def add_project(project_data):
    try:
        response = supabase.table('projects').insert(project_data).execute()
        if response.error:
            st.error(f"Error adding project: {response.error.message}")
        else:
            st.success("Project successfully added!")
    except Exception as e:
        st.error(f"Error adding project: {e}")

def update_project(project_id, updated_data):
    try:
        response = supabase.table('projects').update(updated_data).eq('id', project_id).execute()
        if response.error:
            st.error(f"Error updating project: {response.error.message}")
        else:
            st.success("Project successfully updated!")
    except Exception as e:
        st.error(f"Error updating project: {e}")

def delete_project(project_id):
    try:
        response = supabase.table('projects').delete().eq('id', project_id).execute()
        if response.error:
            st.error(f"Error deleting project: {response.error.message}")
        else:
            st.success("Project deleted successfully!")
    except Exception as e:
        st.error(f"Unexpected error deleting project: {e}")

def get_all_project_files(project_id):
    try:
        with get_connection() as conn: #get_connection still needs to be defined
            df = pd.read_sql(f"SELECT * FROM project_files WHERE project_id = {project_id}", conn)
        return df
    except Exception as e:
        st.error(f"Error fetching project files: {e}")
        return pd.DataFrame()

def upload_file(project_id, uploaded_file):
    if uploaded_file is not None and uploaded_file.name != "":
       file_path = f"project_{project_id}/{uploaded_file.name}"
       res = supabase.storage.from_("project.files").upload(file_path, uploaded_file.getbuffer())
       if res.get("error"):
           st.error(f"Error uploading file to Supabase Storage: {res['error']['message']}")
       else:
           # Simpan metadata ke database jika perlu
           ...
           st.success("File uploaded successfully!")


def delete_file(file_id):
    try:
        with get_connection() as conn: #get_connection still needs to be defined
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM project_files WHERE id=?", (file_id,))
            row = cursor.fetchone()
            if row:
                file_path = row[3]
                response = supabase.storage.from_("project.files").remove([file_path]).execute()
                if response.error:
                    st.error(f"Error deleting file from Supabase: {response.error.message}")
                elif response.status_code == 204:
                    cursor.execute("DELETE FROM project_files WHERE id=?", (file_id,))
                    conn.commit()
                    st.success("File deleted successfully!")
                else:
                    st.error(f"Unexpected error deleting file. Status code: {response.status_code}")
            else:
                st.error("File does not exist.")
    except Exception as e:
        st.error(f"Error deleting file: {e}")

# Streamlit App
st.image("cistech.png", width=450)
st.title("Dashboard Mapping Project TSCM")

tabs = st.tabs(["View Projects", "Add Project", "Edit Project", "Delete Project", "Manage Files"])

with tabs[0]:
    df = get_all_projects()
    if not df.empty:
        display_df = df.rename(columns={
            'project_name': 'Proyek',
            'category': 'Kategori',
            'pic': 'PIC',
            'status': 'Status',
            'date_start': 'Tanggal Mulai',
            'date_end': 'Tanggal Selesai',
            'no_po': 'Nomor PO'
        }).set_index('id')
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("Tidak ada proyek yang ditemukan dalam database.")

with tabs[1]:
    st.subheader("Add New Project")
    with st.form("add_project_form"):
        new_project = st.text_input("Project Name")
        new_category = st.selectbox("Category", ["Project", "Service"])
        new_pic = st.text_input("PIC")
        new_status = st.selectbox("Status", ["Not Started", "Waiting BA", "Not Report", "In Progress", "On Hold", "Completed"])
        new_no_po = st.text_input("PO Number")
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
                    st.error("Please select both start and end dates.")
            else:
                st.error("Project Name and PIC are required!")

with tabs[2]:
    st.subheader("Edit Project")
    df = get_all_projects()
    if df.empty:
        st.info("No projects found in the database.")
    else:
        options = df[['id', 'project_name']]
        selected_option = st.selectbox(
            "Choose a Project to Edit",
            options['id'].tolist(),
            format_func=lambda x: options[options['id'] == x]['project_name'].iloc[0]
        )
        selected_row = df[df['id'] == selected_option].iloc[0]
        with st.form("edit_form"):
            edit_project_name = st.text_input("Project Name", value=selected_row['project_name'])
            edit_category = st.text_input("Category", value=selected_row['category'])
            edit_pic = st.text_input("PIC", value=selected_row['pic'])
            status_options = ['In Progress', 'Completed', 'On Hold']
            edit_status = st.selectbox(
                "Status",
                status_options,
                index=status_options.index(selected_row['status']) if selected_row['status'] in status_options else 0
            )
            start_dt_default = datetime.datetime.strptime(selected_row['date_start'], '%Y-%m-%d').date()
            end_dt_default = datetime.datetime.strptime(selected_row['date_end'], '%Y-%m-%d').date()
            start_dt, end_dt = st.date_input(
                "Select Start and End Dates",
                value=(start_dt_default, end_dt_default),
                min_value=datetime.date.today() - datetime.timedelta(days=365),
                max_value=datetime.date.today() + datetime.timedelta(days=365)
            )
            edit_no_po = st.text_input("PO Number", value=selected_row.get('no_po', ''))
            update_btn = st.form_submit_button(label="Update Project")
            if update_btn:
                updated_data = {
                    'project_name': edit_project_name,
                    'category': edit_category,
                    'pic': edit_pic,
                    'status': edit_status,
                    'date_start': start_dt.isoformat(),
                    'date_end': end_dt.isoformat(),
                    'no_po': edit_no_po
                }
                update_project(selected_option, updated_data)

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
    df_projects = get_all_projects()
    if not df_projects.empty:
        selected_project = st.selectbox(
            "Choose a Project to Manage Files",
            df_projects['id'].tolist(),
            format_func=lambda x: df_projects[df_projects['id'] == x]['project_name'].iloc[0]
        )
        uploaded_file = st.file_uploader("Upload New File Here", type=['pdf', 'docx', 'png', 'jpg', 'jpeg'])
        if st.button("Upload New File"):
            upload_file(selected_project, uploaded_file)
        files_df = get_all_project_files(selected_project)
        for _, row in files_df.iterrows():
            col1, col2, col3 = st.columns([6, 2, 1])
            col1.write(row['file_name'])
            file_url = supabase.storage.from_("project.files").get_public_url(row['file_path'])
            col2.download_button(
                label="Download",
                data=file_url,
                file_name=row['file_name'],
                mime='application/octet-stream',
                key=f'download-{row.id}'
            )
            col3.button(label="Delete", key=row.id, on_click=delete_file, args=(row.id,))

