from src.var.constant import SOURCE_FILE_ENCODINGS


def read_source_file(path):
    last_decode_error = None

    for encoding in SOURCE_FILE_ENCODINGS:
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError as exc:
            last_decode_error = exc

    raise UnicodeError(
        f"Could not decode '{path}'. Save the file as UTF-8 or UTF-8 with BOM."
    ) from last_decode_error
