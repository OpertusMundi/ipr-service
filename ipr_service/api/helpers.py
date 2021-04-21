import os
from ipr_service.loggers import logger


def parse_read_options(form, prefix=''):
    """Extract read options from form data.

    Arguments:
        form (obj): Form object

    Keyword Arguments:
        prefix (str): prefix for the form fields (default: {''})

    Returns:
        (dict): Read options key - value dictionary.
    """
    read_options = {}
    for attr in ['delimiter', 'lat', 'lon', 'geom', 'crs', 'encoding']:
        if getattr(form, prefix+attr).data != '':
            read_options[attr] = getattr(form, prefix+attr).data

    return read_options


def send_file(file):
    """Create a send file response.

    Arguments:
        file (str): Path of the file.

    Returns:
        (obj): Flask response
    """
    from flask import send_file as flask_send_file
    file_content = open(file, 'rb')
    filename = os.path.basename(file)
    response = flask_send_file(file_content, attachment_filename=filename, as_attachment=True)
    response.headers['Content-Length'] = str(os.path.getsize(file))
    return response

def copy_to_output(file, ticket):
    """Copy file to output dir, after creating the containing path.

    Arguments:
        file (str): Path of the file.
        ticket (str): Request ticket.

    Returns:
        (str): Relative to output dir path of the copied file.
    """
    from datetime import datetime
    from shutil import copyfile
    filename = os.path.basename(file)
    output_path = os.path.join(datetime.now().strftime("%y%m"),ticket)
    output_file = os.path.join(output_path, filename)
    full_output = os.path.join(os.environ['OUTPUT_DIR'], output_path)
    os.makedirs(full_output, exist_ok=True)
    copyfile(file, os.path.join(full_output, filename))
    return output_file


def extract_file(file, extraction_dir):
    """Extracts a compressed archive.

    It extracts zipped and tar files. In case the file is neither of them, it returns the same file.

    Arguments:
        file (str): The full path of the file.
        extraction_dir (str): The path where the archive will be extracted.

    Returns:
        (str): The path of the extracted folder, or the initial file if it was not compressed.
    """
    import zipfile
    import tarfile
    path, filename = os.path.split(file)
    os.makedirs(extraction_dir, exist_ok=True)
    if tarfile.is_tarfile(file):
        handle = tarfile.open(file)
        filename = os.path.splitext(filename)[0]
        if filename.endswith('.tar'):
            filename = os.path.splitext(filename)[0]
        file = os.path.join(extraction_dir, filename)
        handle.extractall(file)
        handle.close()
    elif zipfile.is_zipfile(file):
        tgt = os.path.join(extraction_dir, os.path.splitext(filename)[0])
        with zipfile.ZipFile(file, 'r') as handle:
            handle.extractall(tgt)
        file = tgt
    return file
