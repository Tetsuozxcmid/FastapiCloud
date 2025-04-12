import string
from random import choices

def generate_random_string(length: int) ->str:
    return ''.join(choices(string.ascii_letters, k=length))
    
def get_file_data(file_info):
    return {"file_path": file_info.get(b"file_path").decode(), "dell_id": file_info.get(b"dell_id").decode()}