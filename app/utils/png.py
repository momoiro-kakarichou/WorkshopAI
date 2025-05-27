import base64
import struct
import zlib
import os
import io
from mmap import ACCESS_READ, mmap


PNG_MAGIC_NUMBER = b'\x89PNG\r\n\x1a\n'
PNG_MAGIC_NUMBER_SIZE = len(PNG_MAGIC_NUMBER)
CHUNK_LENGTH_SIZE = 4
CHUNK_TYPE_SIZE = 4
CHUNK_CRC_SIZE = 4
TYPE_iTXt = b'iTXt'
TYPE_tEXt = b'tEXt'
TYPE_zTXt = b'zTXt'


def png_read_chunks(png_path: str) -> list:
    """
    Reads the chunks of a PNG file.
    """
    png_file = open(png_path, 'rb')
    if png_file.read(PNG_MAGIC_NUMBER_SIZE) != PNG_MAGIC_NUMBER:
        raise Exception(f'"{png_file.name}" file is not a PNG !')
    
    try:
        png_reader = mmap(png_file.fileno(), 0, access=ACCESS_READ)
    except io.UnsupportedOperation:
        png_reader = png_file
    
    png_reader.seek(PNG_MAGIC_NUMBER_SIZE, os.SEEK_SET)
    chunks = []
    chunks_pos = []
    position = 0
    while True:
        length_byte = png_reader.read(CHUNK_LENGTH_SIZE)

        if not length_byte:
            break

        chunk_length = int.from_bytes(length_byte, byteorder='big')

        chunk_type = png_reader.read(CHUNK_TYPE_SIZE)
        data = png_reader.read(chunk_length)
        crc = png_reader.read(CHUNK_CRC_SIZE)

        chunks_pos.append((position, png_reader.tell()-1))
        position = png_reader.tell()

        current_chunk = {'type': chunk_type, 'data': data, 'crc': crc}
        chunks.append(current_chunk)
    
    return chunks


def is_text_chunk(chunk_type: bytes) -> bool:
    """
    Checks if a chunk type is a text chunk.
    """
    return chunk_type in (TYPE_iTXt, TYPE_tEXt, TYPE_zTXt)

def get_text_chunks(chunks) -> list:
    """
    Retrieves the text chunks from a list of chunks.
    """
    return [chunk for chunk in chunks if is_text_chunk(chunk['type'])]

def chunk_text_decode(text_chunk: dict, proper_name: str):
    """
    Decodes the text from a text chunk if the name matches the proper name.
    """
    data = text_chunk['data']
    name = ''
    text = ''
    naming = True
    for idx, code in enumerate(data):
        if naming:
            if code:
                name += chr(code)
            else:
                naming = False
        else:
            text = data[idx:]
            break
    if name == proper_name:
        return base64.b64decode(text).decode()
    else:
        return None
    

def create_text_chunk(chunk_type: bytes, name: str, text: str) -> bytes:
    """
    Creates a text chunk with the specified type, name, and text.
    """
    if chunk_type not in (TYPE_iTXt, TYPE_tEXt, TYPE_zTXt):
        raise ValueError("Invalid chunk type for text data")

    name_bytes = name.encode('latin1') + b'\x00'
    text_bytes = base64.b64encode(text.encode('utf-8'))
    data = name_bytes + text_bytes

    length = len(data)
    crc = zlib.crc32(chunk_type + data)

    return struct.pack("!I", length) + chunk_type + data + struct.pack("!I", crc)

def add_or_replace_text_chunk_in_png(png_path: str, output_path: str, chunk_type: bytes, name: str, text: str):
    """
    Adds or replaces a text chunk in a PNG file.
    """
    with open(png_path, 'rb') as png_file:
        png_data = png_file.read()

    if png_data[:PNG_MAGIC_NUMBER_SIZE] != PNG_MAGIC_NUMBER:
        raise Exception(f'"{png_path}" is not a valid PNG file!')

    chunks = png_read_chunks(png_path)
    new_chunk = create_text_chunk(chunk_type, name, text)

    existing_chunk_index = None
    for i, chunk in enumerate(chunks):
        if is_text_chunk(chunk['type']):
            decoded_name = chunk_text_decode(chunk, name)
            if decoded_name is not None:
                existing_chunk_index = i
                break

    if existing_chunk_index is not None:
        chunks[existing_chunk_index] = {
            'type': chunk_type,
            'data': new_chunk[8:-4],
            'crc': new_chunk[-4:]
        }
    else:
        chunks.insert(-1, {
            'type': chunk_type,
            'data': new_chunk[8:-4],
            'crc': new_chunk[-4:]
        })

    new_png_data = PNG_MAGIC_NUMBER
    for chunk in chunks:
        length = len(chunk['data'])
        new_png_data += struct.pack("!I", length) + chunk['type'] + chunk['data'] + chunk['crc']

    with open(output_path, 'wb') as output_file:
        output_file.write(new_png_data)
        

# chunks = png_read_chunks('C:/Users/deka/Downloads/Isekai RPG (1).png')
# text_chunks = get_text_chunks(chunks)
# text_data = chunk_text_decode(text_chunks[0], 'chara')
# if text_data:
#     data = json.loads(text_data)
#     s = json.dumps(data, indent=4, sort_keys=True)
#     with open('output.json', 'w') as file:
#         file.write(s)