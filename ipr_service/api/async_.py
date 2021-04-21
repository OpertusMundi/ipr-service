import geovaex
from shutil import rmtree
import os
from uuid import uuid4
import pyproj
from ipr_service.database.actions import db_update_queue_status
from ipr_service.exceptions import NotRasterError, NotVectorError
from ipr_service.lib.raster_ipr import Watermark
from .helpers import copy_to_output, extract_file

def async_callback(future):
    """Generic callback for asynchronous operations.

    Updates database with the results.

    Arguments:
        future (obj): Future object.
    """
    session, result, success, error_msg = future.result()
    ticket = session['ticket']
    if success and os.path.isfile(result):
        result = copy_to_output(result, ticket)
    try:
        rmtree(session['working_path'])
    except:
        pass
    db_update_queue_status(ticket, completed=True, success=success, error_msg=error_msg, result=result)


def _basename(path):
    """Retrieve filename and extension given a full path.

    Arguments:
        path (str): File full path.

    Returns:
        (tuple): filename and extension
    """
    filename = os.path.splitext(os.path.basename(path))
    extension = filename[1]
    filename = filename[0]
    return (filename, extension)


def _open_dataset(path, **kwargs):
    """Open a vector/tabular dataset with (geo)vaex.

    Arguments:
        path (str): Vector file path.
        **kwargs: CRS and read options.

    Returns:
        (geovaex.GeoDataFrame|vaex.DataFrame): Dataframe
    """
    working_path = os.path.dirname(path)
    if os.path.isdir(path):
        path = _validate_dir(path, type_="vector")
    filename, extension = _basename(path)
    arrow_file = os.path.join(working_path, filename + str(uuid4()) + '.arrow')

    crs = kwargs.pop('crs', None)
    df = geovaex.read_file(path, convert=arrow_file, crs=crs, **kwargs)

    return df


def _get_supported_extensions(type_):
    """Retrieves supported raster file extensions from gdal according to installed drivers.

    Arguments:
        type_ (str): 'raster' or 'vector'

    Returns:
        (tuple): Lists with supported file extensions.
    """
    from osgeo import gdal, ogr
    primary = []
    exts = []
    if type_ == "raster":
        driver_count = gdal.GetDriverCount()
        dcap = gdal.DCAP_RASTER
    elif type_ == "vector":
        driver_count = ogr.GetDriverCount()
        dcap = gdal.DCAP_VECTOR
    else:
        raise ValueError("`type_` should be 'raster' or 'vector'")
    for i in range(driver_count):
        drv = gdal.GetDriver(i) if type_=="raster" else ogr.GetDriver(i)
        if drv.GetMetadataItem(dcap):
            ext = drv.GetMetadataItem(gdal.DMD_EXTENSIONS)
            if ext is None or ext=='':
                continue
            ext = ext.split(' ')
            primary.append(ext[0])
            exts.extend(ext)

    if type_ == "vector" and 'tsv' not in exts:
        exts.append('tsv')
    return (primary, exts)


def _validate_dir(path, type_="raster"):
    """Search path for raster file.

    It returns the first supported raster file in path.

    Arguments:
        path (str): Input path

    Raises:
        NotRasterError: when no supported raster found.
        NotVectorError: when no supported vector found.
    """
    exts_primary, exts_all = _get_supported_extensions(type_)
    files = os.listdir(path)
    target = None
    secondary_target = None
    for file in files:
        ext = os.path.splitext(file)[1][1:]
        if ext in exts_primary:
            target = file
            break
        if ext in exts_all and secondary_target is None:
            secondary_target = file
    target = target or secondary_target
    try:
        path = os.path.join(path, target)
    except TypeError:
        if type_ == "raster":
            raise NotRasterError('Compressed file does not contain a raster.')
        else:
            raise NotVectorError('Compressed file does not contain a vector.')

    return path


def _get_export_path(path, working_path):
    """Creates an export path and filename (with extension).

    Arguments:
        path (str): The input file path.
        working_path (str): Working path

    Returns:
        (str): Export file path.
    """
    filename, extension = _basename(path)
    export_path = os.path.join(working_path, 'results')
    os.makedirs(export_path, exist_ok=True)
    return os.path.join(export_path, filename+extension)


def _compress_files(path):
    """Compress files to tar.gz

    All the files contained in a folder will be added to the archive.

    Arguments:
        path (str): The full path of the folder containing the files that will be added to the archive.

    Returns:
        (str): The archived file.
    """
    import tarfile
    if os.path.isdir(path):
        result = path + '.tar.gz'
        with tarfile.open(result, "w:gz") as tar:
            for file in os.listdir(path):
                tar.add(os.path.join(path, file), arcname=file)
    else:
        result = path + '.gz'
        with tarfile.open(result, "w:gz") as tar:
            tar.add(path, arcname=os.path.basename(path))

    return result


def vector_embed_process(embed_type, session, file, uuid, **kwargs):
    """Vector embed process.

    Arguments:
        embed_type (str): Embed type (one of 'fictitious', 'geometries')
        session (dict): Session info
        file (str): Path of input file
        uuid (str): UUID to embed.
        **kwargs: Additional keyword parameters with read options.

    Returns:
        (tuple):
            - (dict): Session info
            - (str): Full path of the resulted file.
            - (bool): Whether operation succeeded.
            - (str): Error message in case of failure.
    """
    try:
        working_path = session['working_path']
        path = extract_file(file, working_path)
        df = _open_dataset(path, **kwargs)

        if embed_type == 'fictitious':
            df = df.ipr.embed_fictitious_entries(uuid)
        elif embed_type == 'geometries':
            df = df.ipr.embed_geometries(uuid)
        else:
            raise ValueError("`embed_type` can be only 'fictitious' or 'geometries'.")

        export_path = _get_export_path(path, working_path)
        if isinstance(df, geovaex.GeoDataFrame):
            driver = df.metadata['driver']
            df.export(export_path, driver=driver, **kwargs)
            pass
        else:
            delimiter = kwargs.pop('delimiter', ',')
            encoding = kwargs.pop('encoding', None)
            df.export_csv(export_path, virtual=False, sep=delimiter, encoding=encoding)
        export_path = _compress_files(export_path)
    except Exception as e:
        return (session, None, False, str(e))

    return (session, export_path, True, None)


def vector_detect_process(detect_type, session, original, test, uuids, **kwargs):
    """Vector detect process.

    Arguments:
        detect_type (str): Detect type (one of 'fictitious', 'geometries')
        session (dict): Session info
        original (str): Path of the original file to test against.
        test (str): Path of the file to test for IPR.
        uuids (list): List of UUIDs to test IPR.
        **kwargs: Additional keyword parameters with read options.

    Returns:
        (tuple):
            - (dict): Session info
            - (str): The detected UUID (None if none is detected).
            - (bool): Whether operation succeeded.
            - (str): Error message in case of failure.
    """
    try:
        working_path = session['working_path']
        original_params = kwargs.pop('original_params', {})
        test_params = kwargs.pop('test_params', {})
        path = extract_file(original, os.path.join(working_path, 'original'))
        df = _open_dataset(path, **original_params)
        path = extract_file(test, os.path.join(working_path, 'test'))
        df_t = _open_dataset(path, **test_params)

        for uuid in uuids:
            if detect_type == 'fictitious':
                check = df.ipr.detect_fictitious_entries(df_t, uuid)
            elif detect_type == 'geometries':
                check = df.ipr.detect_geometries(df_t, uuid)
            else:
                raise ValueError("`detect_type` can be only 'fictitious' or 'geometries'.")
            if check:
                return (session, uuid, True, None)
    except Exception as e:
        return (session, None, False, str(e))

    return (session, None, True, None)


def raster_embed_process(action, session, raster, watermark, crs=None, **kwargs):
    """Raster embed process.

    Arguments:
        action (str): Embed type; one of 'watermark' or 'message'
        session (dict): Session info
        raster (str): Raster path
        watermark (str): Watermark path (in case `action`='watermark') or message to embed (`action`='message')
        **kwargs: Additional parameters for embedding.

    Keyword Arguments:
        crs (str): CRS (default: {None})

    Returns:
        (tuple):
            - (dict): Session info
            - (str): Full path of the resulted file.
            - (bool): Whether operation succeeded.
            - (str): Error message in case of failure.
    """
    epsg = pyproj.CRS.from_user_input(crs).to_epsg() if crs is not None else None
    working_path = session['working_path']
    try:
        path = extract_file(raster, working_path)
        if path != raster and os.path.isdir(path):
            path = _validate_dir(path, type_="raster")
        ipr = Watermark(path, epsg=epsg, tmp=working_path)
        export_path = _get_export_path(path, working_path)
        if action == 'watermark':
            ipr.embed_image(watermark, export_path, **kwargs)
        elif action == 'message':
            ipr.embed_message(export_path, watermark)
        else:
            raise ValueError("`action` should be one of 'watermark' or 'message'")
        export_path = _compress_files(export_path)
    except Exception as e:
        return (session, None, False, str(e))

    return (session, export_path, True, None)


def raster_detect_process(session, original, test):
    """Raster detection process for message embedding.

    Arguments:
        session (str): Session info.
        original (str): Original raster.
        test (str): Watermarked raster.

    Returns:
        (tuple):
            - (dict): Session info
            - (str): The detected message (None if none is detected).
            - (bool): Whether operation succeeded.
            - (str): Error message in case of failure.
    """
    working_path = session['working_path']
    try:
        path = extract_file(original, os.path.join(working_path, 'original'))
        if path != original and os.path.isdir(path):
            path = _validate_dir(path, type_="raster")
        watermarked = extract_file(test, os.path.join(working_path, 'test'))
        if watermarked != test and os.path.isdir(watermarked):
            watermarked = _validate_dir(watermarked, type_="raster")
        ipr = Watermark(path, tmp=working_path)
        msg = ipr.detect_message(watermarked)
    except Exception as e:
        return (session, None, False, str(e))

    return (session, msg, True, None)
