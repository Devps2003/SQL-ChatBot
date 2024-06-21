from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_experimental.sql.base import SQLDatabaseChain
from langchain_core.output_parsers import StrOutputParser
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
import configparser
import os
import sqlite3

def read_properties_file(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file '{file_path}' does not exist.")
    
    config = configparser.ConfigParser()
    config.read(file_path)
    
    gemini_api_key = ""
    
    return gemini_api_key

def get_property():
    file_path = 'config.properties'

    try:
        gemini_api_key = read_properties_file(file_path)
        print("Gemini API Key", gemini_api_key)
        return gemini_api_key
    except FileNotFoundError as e:
        print(e)
        raise e
    
def get_llm(gemini_api_key):
    llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=gemini_api_key, 
                                 convert_system_message_to_human=True, temperature=0.0)
    return llm

def db_connection(db_path):
    db = SQLDatabase.from_uri(f"sqlite:///{db_path}")
    print(db.dialect)
    print(db.get_usable_table_names())
    return db
from langchain.chains import create_sql_query_chain
from langchain.prompts import ChatPromptTemplate
import re
system_prompt = """You are an advanced AI assistant specializing in SQL query formulation and result interpretation. Your primary function is to generate executable SQL queries based on user questions and analyze the results. Follow these strict guidelines:

1. Table Usage: Exclusively use the tables specified in the provided table_info.
2. Query Structure: Always start your query with 'SELECT'. Never include the word 'sql' anywhere in the query.
3. Syntax: Ensure your query is syntactically correct for the {dialect} SQL dialect.
4. Format: 
   - Do not include quotation marks around the query.
   - Avoid using commas to separate lines; use proper SQL syntax instead.
   - Do not add line breaks (\n) in the query.
5. Column Usage: Utilize only the columns listed in the 'Available columns' section.
6. Query Execution: After formulating the query, it will be executed, and you'll interpret the results.

Query Formulation Process:
1. Analyze the user's question carefully.
2. Identify relevant tables and columns from the provided information.
3. Construct a SELECT statement that addresses the user's question.
4. Double-check that the query doesn't start with or include the word 'sql'.
5. Ensure the query is a single, executable SQL statement.

Example of correct query format:
SELECT column1, column2 FROM table WHERE condition

Remember: Your role is to generate only the SQL query. Do not provide any explanations or additional text before or after the query. The query should be ready for direct execution.
"""
def create_conversational_chain(db_path):
    try:
        gemini_api_key = get_property()
        llm = get_llm(gemini_api_key)
        db = db_connection(db_path)

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Table information: {table_info}\n\nAvailable columns: {column_names}\n\nQuestion: {question}")
        ])

        chain = create_sql_query_chain(llm, db)
        
        def get_sql_query_and_result(question: str, column_names: str):
            sql_query = chain.invoke({
                "question": question,
                "table_info": db.get_table_info(),
                "dialect": db.dialect,
                "column_names": column_names
            })
            
            # Clean up the SQL query
            sql_query = clean_sql_query(sql_query)
            
            # Execute the SQL query
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(sql_query)
            result = cursor.fetchall()
            conn.close()
            
            return sql_query, result

        return get_sql_query_and_result, llm
    except Exception as e:
        raise e

def clean_sql_query(sql_query):
    # Remove markdown code blocks
    sql_query = re.sub(r'```sql\s*|\s*```', '', sql_query)
    
    # Remove any 'sql' prefix
    sql_query = re.sub(r'^sql\s*', '', sql_query, flags=re.IGNORECASE)
    
    # Remove any leading/trailing whitespace
    sql_query = sql_query.strip()
    
    return sql_query
