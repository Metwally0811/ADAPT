import subprocess
import threading
import time
import os

def run_flask():
    # Capture stdout and stderr
    process = subprocess.Popen(["python", "Main.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # Read and print output line by line in real-time
    for line in iter(process.stdout.readline, b''):
        print(line.decode().strip())
    process.wait()

def run_gui():
    time.sleep(2)  # Ensure backend has time to start
    subprocess.run(["python", "pyqt.py"])

if __name__ == "__main__":
    # Run Flask in a separate thread so the GUI can start
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True # Allow the main program to exit even if the thread is still running
    flask_thread.start()
    
    run_gui()
