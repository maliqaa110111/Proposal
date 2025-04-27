import streamlit as st
import pandas as pd
import datetime
from supabase import create_client

# Konfigurasi Supabase
url = st.secrets["SUPABASE_URL"]
anon_key = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(url, anon_key)

# --- AUTENTIKASI ---

def login():
    st.title("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        try:
            user = supabase.auth.sign_in(email=email, password=password)
            if user.user:
                st.session_state['user'] = user.user
                st.success("Login berhasil!")
                st.experimental_rerun()
            else:
                st.error("Login gagal, cek email dan password.")
        except Exception as e:
            st.error(f"Error login: {e}")

def signup():
    st.title("Sign Up")
    email = st.text_input("Email untuk registrasi", key="signup_email")
    password = st.text_input("Password", type="password", key="signup_password")
    if st.button("Sign Up"):
        try:
            user = supabase.auth.sign_up({"email": email, "password": password})
            if user.user:
                st.success("Registrasi berhasil! Silakan login.")
            else:
                st.error("Gagal registrasi.")
        except Exception as e:
            st.error(f"Error sign up: {e}")

def logout():
    supabase.auth.sign_out()
    st.session_state.pop('user', None)
    st.success("Logout berhasil!")
    st.experimental_rerun()

# --- CRUD PROJECT ---

def get_projects():
    user = st.session_state['user']
    response = supabase.table('projects').select('*').eq('user_id', user.id).execute()
    if response.error:
        st.error(f"Error mengambil data: {response.error.message}")
        return pd.DataFrame()
    df = pd.DataFrame(response.data)
    df.insert(0, 'No', range(1, len(df) + 1))
    return df

def add_project(name, category, pic):
    user = st.session_state['user']
    data = {'name': name, 'category': category, 'pic': pic, 'user_id': user.id}
    response = supabase.table('projects').insert(data).execute()
    if response.error:
        st.error(f"Error menambah project: {response.error.message}")
    else:
        st.success("Project berhasil ditambahkan!")

def edit_project(project_id, name, category, pic):
    response = supabase.table('projects').update({'name': name, 'category': category, 'pic': pic}).eq('id', project_id).execute()
    if response.error:
        st.error(f"Error update project: {response.error.message}")
    else:
        st.success("Project berhasil diperbarui!")

def delete_project(project_id):
    # Hapus file terkait dulu (opsional)
    files_resp = supabase.storage.from_('project_files').list(f"projects/{project_id}/")
    if files_resp.data:
        paths = [f"projects/{project_id}/{f['name']}" for f in files_resp.data]
        supabase.storage.from_('project_files').remove(paths)
    # Hapus project
    response = supabase.table('projects').delete().eq('id', project_id).execute()
    if response.error:
        st.error(f"Error hapus project: {response.error.message}")
    else:
        st.success("Project berhasil dihapus!")

# --- FILE MANAGEMENT ---

def upload_file(project_id, file):
    try:
        path = f"projects/{project_id}/{file.name}"
        res = supabase.storage.from_('project_files').upload(path, file)
        if res.error:
            st.error(f"Error upload file: {res.error.message}")
        else:
            st.success("File berhasil diupload!")
    except Exception as e:
        st.error(f"Error upload file: {e}")

def list_files(project_id):
    res = supabase.storage.from_('project_files').list(f"projects/{project_id}/")
    if res.error:
        st.error(f"Error list files: {res.error.message}")
        return []
    return [f['name'] for f in res.data]

def delete_file(project_id, filename):
    path = f"projects/{project_id}/{filename}"
    res = supabase.storage.from_('project_files').remove([path])
    if res.error:
        st.error(f"Error hapus file: {res.error.message}")
    else:
        st.success("File berhasil dihapus!")

# --- UI ---

def main_app():
    st.title("Dashboard Mapping Project TSCM")
    user = st.session_state['user']

    st.sidebar.write(f"Logged in as: {user.email}")
    if st.sidebar.button("Logout"):
        logout()

    menu = st.sidebar.selectbox("Menu", ["View Projects", "Add Project", "Manage Files"])

    if menu == "View Projects":
        projects = get_projects()
        if projects.empty:
            st.info("Belum ada project.")
            return
        st.dataframe(projects[['No', 'name', 'category', 'pic']].rename(columns={
            'name': 'Project',
            'category': 'Category',
            'pic': 'PIC'
        }))
        for _, row in projects.iterrows():
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Edit {row['No']}"):
                    edit_project_page(row['id'])
                    return
            with col2:
                if st.button(f"Delete {row['No']}"):
                    delete_project(row['id'])
                    st.experimental_rerun()

    elif menu == "Add Project":
        st.header("Tambah Project Baru")
        name = st.text_input("Nama Project")
        category = st.text_input("Kategori")
        pic = st.text_input("PIC")
        if st.button("Tambah"):
            if name and category and pic:
                add_project(name, category, pic)
                st.experimental_rerun()
            else:
                st.warning("Semua field harus diisi!")

    elif menu == "Manage Files":
        projects = get_projects()
        if projects.empty:
            st.info("Belum ada project.")
            return
        project_names = projects['name'].tolist()
        selected_project = st.selectbox("Pilih Project", project_names)
        project_id = projects[projects['name'] == selected_project]['id'].values[0]

        st.subheader(f"Kelola File untuk Project: {selected_project}")

        uploaded_file = st.file_uploader("Upload File")
        if uploaded_file:
            if st.button("Upload File"):
                upload_file(project_id, uploaded_file)
                st.experimental_rerun()

        files = list_files(project_id)
        if files:
            st.write("Daftar File:")
            for f in files:
                col1, col2 = st.columns([8, 1])
                col1.write(f)
                with col2:
                    if st.button(f"Hapus {f}"):
                        delete_file(project_id, f)
                        st.experimental_rerun()
        else:
            st.info("Belum ada file di project ini.")

def edit_project_page(project_id):
    project_resp = supabase.table('projects').select('*').eq('id', project_id).single().execute()
    if project_resp.error or not project_resp.data:
        st.error("Project tidak ditemukan.")
        return
    proj = project_resp.data
    st.header(f"Edit Project: {proj['name']}")
    name = st.text_input("Nama Project", value=proj['name'])
    category = st.text_input("Kategori", value=proj['category'])
    pic = st.text_input("PIC", value=proj['pic'])
    if st.button("Update"):
        if name and category and pic:
            edit_project(project_id, name, category, pic)
            st.experimental_rerun()
        else:
            st.warning("Semua field harus diisi!")

if __name__ == "__main__":
    if 'user' not in st.session_state:
        login()
    else:
        main_app()
