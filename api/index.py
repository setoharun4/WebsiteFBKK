import sys
import os

# Memastikan Vercel bisa membaca file server_improved.py di root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server_improved import app

if __name__ == '__main__':
    app.run()
