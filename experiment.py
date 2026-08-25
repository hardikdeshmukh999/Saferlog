import sqlite3
import httpx

def run_experiment():
    conn = sqlite3.connect('audit.db')
    
    # 1. Modify to doc-993
    print("Modifying record 3 to doc-993...")
    conn.execute("UPDATE events SET resource_id='doc-993' WHERE id=3")
    conn.commit()

    verify_fail = httpx.get('http://127.0.0.1:8000/audit/verify').json()
    print('After Tampering:', verify_fail)

    # 2. Modify back to doc-992
    print("\nModifying record 3 back to doc-992...")
    conn.execute("UPDATE events SET resource_id='doc-992' WHERE id=3")
    conn.commit()

    verify_restore = httpx.get('http://127.0.0.1:8000/audit/verify').json()
    print('After Restoring:', verify_restore)
    
if __name__ == "__main__":
    run_experiment()
