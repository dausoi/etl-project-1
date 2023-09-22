import sqlite3
import os

def db_init(db):
    try:
        print("Deleting the database file (if any)...")
        os.remove(f"{db}.db")
    except FileNotFoundError:
        pass
    
    print("Connecting to a new database file")
    con = sqlite3.connect(f"{db}.db")
    cur = con.cursor()
    
    print("Initializing new tables and constraints")
    cur.execute("""CREATE TABLE IF NOT EXISTS entry (
                entry_id integer NOT NULL,
                url text NOT NULL,
                last_modified NOT NULL,
                PRIMARY KEY("entry_id" AUTOINCREMENT),
                UNIQUE("url", "last_modified"))
                """)
    cur.execute("""CREATE TABLE IF NOT EXISTS book_info (
                book_info_id integer, 
                isbn text, 
                title text, 
                author text,
                translator text,
                year text,
                num_pages integer, 
                product_category text,
                suggested_price decimal,
                entry_id integer REFERENCES entry (entry_id),
                PRIMARY KEY (book_info_id AUTOINCREMENT))
                """)
    con.commit()
    print("Closing connection...")
    con.close()
    print("Initialization finished.")

# display_sample("entry")
db_init()