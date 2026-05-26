import streamlit as st
from database.database import (
    get_company_materials,
    delete_company_material
)

def show_materials_page():

    st.header("Материалы компании")

    if "user_id" not in st.session_state:
        st.info("Войдите как стажёр.")
        return

    materials = get_company_materials(
        st.session_state["user_id"]
    )

    if not materials:
        st.info("Материалы пока не загружены.")
        return

    st.write(f"Загружено файлов: {len(materials)}")

    for index, material in enumerate(materials):

        file_name = material[0]
        content = material[1]

        with st.expander(f"📄 {file_name}"):

            preview = content[:1000]

            st.text_area(
                "Предпросмотр",
                preview,
                height=200,
                key=f"material_preview_{index}"
            )
            if st.button(
                    "🗑 Удалить файл",
                    key=f"delete_material_{index}"
                ):

                    delete_company_material(
                        st.session_state["user_id"],
                        file_name
                    )

                    st.success("Файл удалён")

                    st.rerun()