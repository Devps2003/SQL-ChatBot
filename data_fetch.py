import requests
import pandas as pd
import sqlite3
from sqlite3 import Error
from frappeclient import FrappeClient

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
        # Connect to SQLite database
        conn = sqlite3.connect(db_name)
        # Save DataFrame to SQLite table
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        # Commit the transaction
        conn.commit()
        print(f"Data saved to SQLite database '{db_name}' in table '{table_name}'")
    except Error as e:
        print(f"Error: {e}")
    finally:
        # Close the database connection
        if conn:
            conn.close()

# Usage example
doctype = "Purchase Order"
df = fetch_all_data(doctype)
if df is not None:
    db_name = "db.db"
    table_name = "purchase_orders"
    save_to_sqlite(df, db_name, table_name)
else:
    print("Failed to fetch data.")
