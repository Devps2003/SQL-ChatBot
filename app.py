import streamlit as st
from streamlit_chat import message
from PIL import Image
import os
import requests
import pandas as pd
import sqlite3
from sqlite3 import Error
from frappeclient import FrappeClient

import utils

# Configuration
url = "http://43.205.39.54"
api_key = "1a7902ee177ab14"
secret_key = "98a82ed1faeff06"

def fetch_all_data(doctype):
    client = FrappeClient(url)
    client.authenticate(api_key, secret_key)

    try:
        items = client.get_list(doctype, limit_start=0, limit_page_length=25000)
        df = pd.DataFrame(items)
        return df
    except Exception as e:
        if hasattr(e, 'response') and e.response.status_code == 400:
            print("Failed to fetch data. Status code:", e.response.status_code)
            print("Response content:", e.response.content)
            return None
        else:
            raise e

def save_to_sqlite(df, db_name, table_name):
    try:
        conn = sqlite3.connect(db_name)
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        conn.commit()
        print(f"Data saved to SQLite database '{db_name}' in table '{table_name}'")
    except Error as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()
def get_column_names(db_name, table_name):
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        return column_names
    except Error as e:
        print(f"Error: {e}")
        return []
    finally:
        if conn:
            conn.close()

def initialize_session_state():
    st.session_state.setdefault('history', [])
    st.session_state.setdefault('generated', ["Hello! I am here to provide answers to questions fetched from Database."])
    st.session_state.setdefault('past', ["Hello Buddy!"])
    st.session_state.setdefault('column_names', [])

def display_chat(get_sql_query, llm):
    reply_container = st.container()
    container = st.container()

    with container:
        with st.form(key='chat_form', clear_on_submit=True):
            user_input = st.text_input("Question:", placeholder="Ask me questions from uploaded PDF", key='input')
            submit_button = st.form_submit_button(label='Send ⬆️')
        
        if submit_button and user_input:
            generate_response(user_input, get_sql_query, llm)
    
    display_generated_responses(reply_container)

def generate_response(user_input, get_sql_query, llm):
    with st.spinner('Spinning a snazzy reply...'):
        output = conversation_chat(user_input, get_sql_query, llm, st.session_state['history'], st.session_state['column_names'])

    st.session_state['past'].append(user_input)
    st.session_state['generated'].append(str(output))  # Ensure output is a string

def conversation_chat(user_input, get_sql_query_and_result, llm, history, column_names):
    sql_query, query_result = get_sql_query_and_result(user_input, ", ".join(column_names))
    
    context = f"SQL Query: {sql_query}\nUser Question: {user_input}\nAvailable Columns: {', '.join(column_names)}\nQuery Result: {query_result}"
    prompt = f"Based on this SQL query, context, and query result, provide a human-readable response: {context}"
    
    response = llm.invoke(prompt)
    
    # Ensure we're working with a string response
    if hasattr(response, 'content'):
        response_text = response.content
    elif isinstance(response, dict) and 'text' in response:
        response_text = response['text']
    else:
        response_text = str(response)

    history.append((user_input, response_text))
    return response_text

def display_generated_responses(reply_container):
    if st.session_state['generated']:
        with reply_container:
            for i in range(len(st.session_state['generated'])):
                message(st.session_state["past"][i], is_user=True, key=f"{i}_user", avatar_style="adventurer")
                message(str(st.session_state["generated"][i]), key=str(i), avatar_style="bottts")

def fetch_and_save_data(doctype):
    df = fetch_all_data(doctype)
    if df is not None:
        db_name = f"{doctype.lower().replace(' ', '_')}.db"
        table_name = doctype.lower().replace(' ', '_')
        save_to_sqlite(df, db_name, table_name)
        st.success(f"Data for {doctype} fetched and saved successfully!")
    else:
        st.error(f"Failed to fetch data for {doctype}.")

def main():
    initialize_session_state()
    
    st.title("Genie")

    image = Image.open('chatbot.jpg')
    st.image(image, width=150)
    
    hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    doctypes = ["Purchase Order", "Item", "Item Price", "Customer", "Material Request"]
    selected_doctype = st.selectbox("Select Doctype", doctypes)

    
    if selected_doctype:
        db_name = f"{selected_doctype.lower().replace(' ', '_')}.db"
        table_name = selected_doctype.lower().replace(' ', '_')

        if os.path.exists(db_name):
            st.success(f"Database for {selected_doctype} already exists.")
            st.session_state['column_names'] = get_column_names(db_name, table_name)
        else:
            if st.button("Fetch Data"):
                fetch_and_save_data(selected_doctype)
                st.session_state['column_names'] = get_column_names(db_name, table_name)

        if os.path.exists(db_name):
            get_sql_query_and_result, llm = utils.create_conversational_chain(db_name)
            display_chat(get_sql_query_and_result, llm)
if __name__ == "__main__":
    main()