import subprocess
import os
import sys
import signal
import threading

def stream_output(process, name):
    """Stream output from a process to console."""
    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                print(f"[{name}] {line}", end='')
    except:
        pass

if __name__ == "__main__":
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Start FastAPI server and Node server in parallel
    processes = []
    threads = []
    
    # Set UTF-8 encoding for subprocesses to handle emojis/unicode
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    
    try:
        print("🚀 Starting Inspectra servers...\n")
        
        # Start FastAPI server
        print("📘 Starting FastAPI server: uvicorn backend:app --reload\n")
        fastapi_process = subprocess.Popen(
            "uvicorn backend:app --reload",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            bufsize=1,
            shell=True,
            cwd=script_dir,
            env=env
        )
        processes.append(("FastAPI", fastapi_process))
        
        # Start Node server
        print("📗 Starting Node server: npm run dev\n")
        node_process = subprocess.Popen(
            "npm run dev",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            bufsize=1,
            shell=True,
            cwd="C:\\Inspectra\\inspectrai",
            env=env
        )
        processes.append(("Node", node_process))
        
        # Start threads to stream output from both processes
        for name, proc in processes:
            thread = threading.Thread(target=stream_output, args=(proc, name), daemon=True)
            thread.start()
            threads.append(thread)
        
        # Keep processes running
        while True:
            all_running = all(proc.poll() is None for _, proc in processes)
            if not all_running:
                break
            import time
            time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n\n⛔ Shutting down servers...")
        for name, proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
                print(f"✅ {name} server stopped")
            except subprocess.TimeoutExpired:
                proc.kill()
                print(f"⚠️ {name} server killed")
    except Exception as e:
        print(f"❌ Error: {e}")
        for name, proc in processes:
            try:
                proc.terminate()
            except:
                pass
        sys.exit(1)
