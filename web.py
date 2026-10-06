import logging
import os

from waitress import serve

from zubryk import storage
from zubryk.storage.exams import setup_exam_storage
from zubryk.web.app import create_app

app=create_app()

if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)
    storage.setup_database()
    setup_exam_storage()
    serve(app,host="127.0.0.1",port=int(os.environ.get("PORT","8088")),threads=8)
