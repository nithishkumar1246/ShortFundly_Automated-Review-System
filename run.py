import os
import sys
import uvicorn

if __name__ == "__main__":
    # Ensure backend directory is in python path
    backend_dir = os.path.join(os.path.dirname(__file__), "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
        
    print("=================================================================")
    print("  AUTOMATED INTERN REVIEW, TASK ALLOCATION & EVALUATION SYSTEM   ")
    print("=================================================================")
    print("  Starting Enterprise AI Review Engine on http://127.0.0.1:8000  ")
    print("=================================================================")
    
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True, app_dir=backend_dir)
