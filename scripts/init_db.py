import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from zubryk import storage
from zubryk.storage.exams import setup_exam_storage

if __name__=="__main__":
    storage.setup_database()
    setup_exam_storage()
    print("Additive schema and word catalog ready")
