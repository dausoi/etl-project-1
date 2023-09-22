from datetime import datetime
from pathlib import Path
from collections import deque
from bs4 import BeautifulSoup
import sqlite3
import xmltodict
import requests
import time

BOOKSCAPE_XML_URL = "https://bookscape.co/sitemap.xml"
XML_DIR = "./book-links"
BOOKSCAPE_DB_FILE = "books.db"
KIDSCAPE_CAT_NAME = "KIDSCAPE"

def get_bookscape_xml():

    book_file_path = Path(f"{XML_DIR}/bookscape-{datetime.strftime(datetime.now(),'%Y-%m-%d_%H:%M:%S')}.xml")
    book_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # xml_text = requests.get(BOOKSCAPE_XML_URL).text
    xml_content = requests.get(BOOKSCAPE_XML_URL)
    with open(book_file_path, "w+") as f:
        f.write(xml_content.text)
    return book_file_path

def extract_bookscape_xml(bookscape_xml_path):
    book_urls = deque()
    urlset = xmltodict.parse(Path(f"{bookscape_xml_path}").read_bytes())['urlset']['url']
    for url in urlset:
        loc, lastmod = url['loc'], url['lastmod']
        if loc.startswith(("https://bookscape.co/books/in-stock", 
                           "https://bookscape.co/books/kidscape")):
            book_urls.append((loc, lastmod,))
    return book_urls

def update_entry_table(book_urls):
    con = sqlite3.connect(BOOKSCAPE_DB_FILE)
    cur = con.cursor()
    for book_url in book_urls:
        in_entry = cur.execute("""SELECT url, last_modified FROM entry
                                    WHERE url = ? AND last_modified = ?
                                    """, (book_url[0], book_url[1], )).fetchall()
        if not in_entry:
            cur.execute("INSERT INTO entry (url, last_modified) VALUES (?, ?);", (book_url[0], book_url[1],))
            rowid = cur.execute("SELECT last_insert_rowid();").fetchone()[0]
            print(f"Inserting entry_id {rowid}: {book_url[0]}")
            _update_book_info(book_url[0], rowid, con)
            con.commit()
            time.sleep(10) # Be gentle to the server.
    con.close()

def _update_book_info(bookscape_url, entry_id, connection):
    con = connection
    cur = con.cursor()
    response = requests.get(bookscape_url)
    soup = BeautifulSoup(response.text, "lxml")

    is_kidscape = bookscape_url.startswith("https://bookscape.co/books/kidscape")

    # TODO: Error handling to skip an expection (AttributeError)
    
    # Elements to use in ternary operators
    isbn_elem = soup.find("span", class_="sku")
    price_elem = soup.find("p", class_="price")
    # Some books have discount, substitute the entire tag (the p elem) with discount scope (the ins elem)
    price_elem = price_elem.ins if price_elem.ins else price_elem    
    
    # Data to insert: isbn, title, author, translator, num_pages, year, suggested_price, product_category, entry_id (implicit)
    table_data = {row.th.text: row.td.text for row in soup.find_all("tr")}
    isbn = "".join(isbn_elem.text.split("-")) if isbn_elem else None
    title = soup.find("h1", class_="product_title entry-title").text
    author = table_data.get("ผู้เขียน")
    translator = table_data.get("ผู้แปล")
    year = table_data.get("ปีที่พิมพ์")
    num_pages = int(table_data.get("จำนวนหน้า").split()[0])
    product_category = soup.find("nav", class_="woocommerce-breadcrumb").text.split("›")[3].strip() if not is_kidscape else KIDSCAPE_CAT_NAME
    suggested_price = price_elem.text.strip().split()[0] if price_elem.text else 0    
    
    cur.execute("""INSERT INTO book_info (isbn, title, author, translator, year, num_pages, product_category, suggested_price, entry_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (isbn, title, author, translator, year, num_pages, product_category, suggested_price, entry_id, ))
    
    con.commit()
    
def main():
    bookscape_xml = get_bookscape_xml()
    in_stock_books_data = extract_bookscape_xml(bookscape_xml)
    update_entry_table(in_stock_books_data)

main()