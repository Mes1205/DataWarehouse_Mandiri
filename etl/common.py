# etl/common.py
# Helper bersama untuk modul ETL (dimensi & fakta).

import os
import sys

# Tambahkan root project ke sys.path supaya `from config import ...` tetap
# berjalan walau modul ini ada di dalam package etl/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from config import DATA_DIR


def _read_source_csv(filename):
    """Baca CSV dari DATA_DIR. Return None jika file tidak ada — supaya satu
    folder DATA_DIR boleh hanya berisi sebagian file (mis. cuma nasabah,
    merchant, transaksi). Separator ';' atau ',' dideteksi otomatis dari header."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        header = f.readline()
    sep = ';' if header.count(';') >= header.count(',') else ','
    return pd.read_csv(path, sep=sep)
