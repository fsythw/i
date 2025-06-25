from tinydb import TinyDB, Query
import hashlib

db = TinyDB('hash_cache.json')
File = Query()

def compute_file_hash(uploaded_file, buf_size=65536):
    md5 = hashlib.md5()
    uploaded_file.seek(0)
    while True:
        data = uploaded_file.read(buf_size)
        if not data:
            break
        md5.update(data)
    uploaded_file.seek(0)
    return md5.hexdigest()

def is_cached(file_hash):
    return db.contains(File.hash == file_hash)

def add_to_cache(file_hash, filename, metadata_path):
    db.insert({'hash': file_hash, 'filename': filename, 'metadata_path': metadata_path})

