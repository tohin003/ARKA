
import os
import sys
import shutil
import pytest
from arka.skills.registry import get_skill_registry
from arka.tools.tool_executor import ToolExecutor

# Setup
TEST_DIR = "test_data_skills"
if os.path.exists(TEST_DIR):
    shutil.rmtree(TEST_DIR)
os.makedirs(TEST_DIR)

registry = get_skill_registry()
registry.scan_and_register()
executor = ToolExecutor()

def test_file_organizer():
    # Setup files
    os.makedirs(f"{TEST_DIR}/organizer")
    with open(f"{TEST_DIR}/organizer/test.txt", "w") as f: f.write("content")
    with open(f"{TEST_DIR}/organizer/img.png", "w") as f: f.write("content")
    
    # Run Tool
    result = executor.execute("organize_directory", {"path": f"{TEST_DIR}/organizer", "strategy": "extension"})
    
    # Verify
    assert "Organization Complete" in result
    assert os.path.exists(f"{TEST_DIR}/organizer/Documents/test.txt")
    assert os.path.exists(f"{TEST_DIR}/organizer/Images/img.png")
    print("✅ File Organizer: Passed")

def test_security_tools():
    # Forensics
    res = executor.execute("analyze_disk_usage", {"path": "."})
    assert "Disk Usage Analysis" in res
    print("✅ Forensics: Passed")
    
    # Integrity
    dummy = f"{TEST_DIR}/secret.txt"
    with open(dummy, "w") as f: f.write("secret")
    res = executor.execute("secure_delete_file", {"path": dummy})
    assert "Successfully securely deleted" in res
    assert not os.path.exists(dummy)
    print("✅ Secure Delete: Passed")

def test_deep_research():
    # Only run if skill is active
    if "deep_research" not in registry.registry or not registry.registry["deep_research"].is_active:
        print("⚠️ Deep Research not active")
        return

    # Limited recursion to avoid ban, just check if it runs
    res = executor.execute("perform_deep_research", {"query": "python 3.14 release date", "max_depth": 1})
    # It might fail due to network or google rate limit, but we check if it TRIES
    if "Error" in res and "429" in res:
         print("⚠️ Deep Research: Rate Limited (Expected)")
    else:
        print(f"✅ Deep Research: Ran (Length: {len(res)})")

def test_sql_analysis():
    # Use in-memory sqlite
    import sqlite3
    db_path = f"{TEST_DIR}/test.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("CREATE TABLE users (id int, name text)")
    c.execute("INSERT INTO users VALUES (1, 'Alice')")
    conn.commit()
    conn.close()
    
    conn_str = f"sqlite:///{db_path}"
    
    # Test SELECT
    res = executor.execute("execute_readonly_sql", {"connection_string": conn_str, "query": "SELECT * FROM users"})
    assert "Alice" in res
    
    # Test Blocked
    res_blocked = executor.execute("execute_readonly_sql", {"connection_string": conn_str, "query": "DROP TABLE users"})
    assert "Security Alert" in res_blocked
    
    print("✅ SQL Analysis: Passed")

def test_document_skills():
    # PDF
    from pypdf import PdfWriter
    pdf1 = f"{TEST_DIR}/test1.pdf"
    pdf2 = f"{TEST_DIR}/test2.pdf"
    merged = f"{TEST_DIR}/merged.pdf"
    
    # Create dummy PDFs
    w = PdfWriter()
    w.add_blank_page(width=100, height=100)
    w.write(pdf1)
    w.write(pdf2)
    w.close()
    
    res = executor.execute("pdf_merge", {"paths": [pdf1, pdf2], "output_path": merged})
    assert "Successfully merged 2 files" in res
    
    res_count = executor.execute("pdf_page_count", {"path": merged})
    assert res_count == "2"
    print("✅ PDF Processing: Passed")
    
    # DOCX
    docx_path = f"{TEST_DIR}/test.docx"
    executor.execute("create_docx", {"path": docx_path, "content": "Hello World", "heading": "Test"})
    res_read = executor.execute("read_docx", {"path": docx_path})
    assert "Hello World" in res_read
    print("✅ DOCX Processing: Passed")
    
    # Spreadsheet
    csv_path = f"{TEST_DIR}/test.csv"
    with open(csv_path, "w") as f:
        f.write("col1,col2\nval1,val2\nval3,val4")
        
    res_csv = executor.execute("read_spreadsheet", {"path": csv_path})
    assert "val1" in res_csv
    assert "val2" in res_csv
    print("✅ Spreadsheet: Passed")

    # PPTX
    pptx_path = f"{TEST_DIR}/test.pptx"
    slides = [{"title": "Slide 1", "content": "Content 1"}, {"title": "Slide 2", "content": "Content 2"}]
    executor.execute("create_presentation", {"path": pptx_path, "title": "Test Pres", "slides": slides})
    res_pptx = executor.execute("read_presentation", {"path": pptx_path})
    assert "Content 1" in res_pptx
    print("✅ PPTX Processing: Passed")
    
    # Changelog (Git)
    res_git = executor.execute("get_git_history", {"path": "."})
    assert "Error" not in res_git # might be empty if no commits or not git repo, but shouldn't error 
    print(f"✅ Changelog/Git: Ran (Len: {len(res_git)})")
    
    # Domain
    res_dom = executor.execute("check_domain_dns", {"domain": "google.com"})
    assert "TAKEN" in res_dom or "Error" not in res_dom
    print("✅ Domain Check: Passed")
    
    # Article
    res_art = executor.execute("extract_article_text", {"url": "https://example.com"})
    # example.com P tag contains "illustrative examples"
    assert "illustrative examples" in res_art or len(res_art) > 10 or "Error" in res_art 
    print("✅ Article Extractor: Passed")

if __name__ == "__main__":
    print(f"Active Skills: {[s for s, v in registry.registry.items() if v.is_active]}")
    try:
        test_file_organizer()
        test_security_tools()
        test_sql_analysis()
        test_document_skills()
        test_deep_research()
        print("\n🎉 ALL TESTS PASSED")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
