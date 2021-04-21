from osgeo import gdal, osr
from PIL import Image
import numpy as np
import numpy.ma as ma
import pywt
import qrcode
from pyzbar.pyzbar import decode
import os
import tempfile

def scramble(matrix, iterations=1):
    """Scramble a two-dimensional array.

    Scrambles an array using Arnolds transformation.

    Arguments:
        matrix (numpy.array): Original array

    Keyword Arguments:
        iterations (int): Number of iterations (default: {1})

    Returns:
        (numpy.array): Scrambled array
    """
    iterations -= 1
    N = len(matrix)
    scrambled = np.array([np.array([False]*N)]*N)
    for y in range(1, N+1):
        for x in range(1, N+1):
            x_ = (x + y)%N
            y_ = (x + 2*y)%N
            scrambled[y_-1][x_-1] = matrix[y-1][x-1]
    if iterations > 0:
        scrambled = scramble(scrambled, iterations=iterations)
    return scrambled


def unscramble(scrambled, iterations=1):
    """Recovers the original array from a scrambled array.

    Applies the inverse Arnolds transformation.

    Arguments:
        scrambled (numpy.array): Scrambled array.

    Keyword Arguments:
        iterations (int): Number of iterations - should be the number of iterations used to scramble the array in order to recover it (default: {1})

    Returns:
        (numpy.array): Original array
    """
    iterations -= 1
    N = len(scrambled)
    matrix = np.array([np.array([False]*N)]*N)
    for y in range(1, N+1):
        for x in range(1, N+1):
            x_ = (2*x - y)%N
            y_ = (-x + y)%N
            matrix[y_-1][x_-1] = scrambled[y-1][x-1]
    if iterations > 0:
        matrix = unscramble(matrix, iterations=iterations)
    return matrix

def createQR(msg, dim=None):
    """Create a QR-code image.

    Arguments:
        msg (str): The message to embed.

    Keyword Arguments:
        dim (int): If not None, the QR-code will be resized to this dimension (in pixels; default: {None})

    Returns:
        (obj): PIL Image
    """

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(msg)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    if dim is not None:
        img = img.resize((dim, dim))

    return img


class Watermark(object):
    """Collection of methods to embed and extract visible and invisible watermarks to rasters.

    Embed a watermark to raster or encrypt/detect an invisible message to/from the raster.
    """

    def __init__(self, file, epsg=None, tmp=None):
        """Open a raster file, in order to embed a watermark or uuid.

        Arguments:
            file (str): (Full) path of the raste file.
            epsg (int): EPSG code
        """
        raster = gdal.Open(file, gdal.GA_ReadOnly)
        if epsg is not None:
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(epsg)
            ds.SetSpatialRef(srs)
        mode, bandInterp = self.getBandInterpretation(raster)
        self.tmp = tmp if tmp is not None else os.path.join(tempfile.gettempdir(), 'raster_ipr')
        os.makedirs(self.tmp, exist_ok=True)
        self._driver = raster.GetDriver()

        if mode == 'Palette':
            band = raster.GetRasterBand(bandInterp['Palette'])
            self._paletteCount = band.GetRasterColorTable().GetCount()
            temp_file = self._appendToFilename(file, '-toRGB')
            raster = gdal.Translate(temp_file, raster, rgbExpand='rgba')
            raster = None
            raster = gdal.Open(temp_file, gdal.GA_ReadOnly)
            mode, bandInterp = self.getBandInterpretation(raster)
        else:
            self._paletteCount = None

        self._raster = raster
        self._mode = mode
        self._band_interpretation = bandInterp
        self._embedded = None

    @property
    def mode(self):
        """Raster mode"""
        return self._mode

    @property
    def band_interpretation(self):
        """Raster band interpretation"""
        return self._band_interpretation

    @property
    def raster(self):
        """gdal raster dataset"""
        return self._raster

    @property
    def driver(self):
        """Image driver"""
        return self._driver

    @property
    def paletteCount(self):
        """If image mode is indexed, the number of colors in the palette"""
        return self._paletteCount


    def getBandInterpretation(self, ds):
        """Get image mode and band interpretation.

        Arguments:
            ds (osgeo.gdal.Dataset): Raster dataset.

        Raises:
            NotImplementedError: When image mode is not supported.
        Returns:
            (tuple):
                - (str): image mode; one of 'grayscale', 'RGB', 'RGBA', 'Palette'.
                - (dict): Band interpretation; dictionary with key the color name and value the band number.
        """
        count = ds.RasterCount
        bandInterp = {}
        for i in range(count):
            i += 1
            band = ds.GetRasterBand(i)
            if band is None:
                continue
            color = gdal.GetColorInterpretationName(band.GetColorInterpretation())
            if color in ['Red', 'Green', 'Blue', 'Gray', 'Alpha', 'Palette']:
                bandInterp[color] = i
        colors = list(bandInterp.keys())
        if 'Gray' in colors:
            mode = 'grayscale'
        elif 'Red' in colors and 'Green' in colors and 'Blue' in colors and len(colors) == 3:
            mode = 'RGB'
            if count == 4 and 4 not in list(bandInterp.values()):
                band = ds.GetRasterBand(4)
                color = gdal.GetColorInterpretationName(band.GetColorInterpretation())
                max_value = band.GetStatistics(False, True)[1]
                if color == 'Undefined' and max_value < 256:
                    mode = 'RGBA'
                    bandInterp['Alpha'] = 4
        elif 'Red' in colors and 'Green' in colors and 'Blue' in colors and 'Alpha' in colors and len(colors) == 4:
            mode = 'RGBA'
        elif 'Palette' in colors:
            mode = 'Palette'
        else:
            raise NotImplementedError('Only Grayscale, RGB(A), and color-mapped rasters are supported.')
        return (mode, bandInterp)


    def _appendToFilename(self, filename, string):
        """Append a string to filename.

        Arguments:
            filename (str): The filename or full path to append the string.
            string (str): The string to append.

        Returns:
            (str): The resulted filename.
        """
        basename = os.path.splitext(os.path.basename(filename))
        ext = basename[1]
        basename = basename[0]
        return os.path.join(self.tmp, basename + string + ext)


    def _getBackground(self, mode):
        """Get background depending on the image mode.

        Arguments:
            mode (int): The image mode.

        Returns:
            (tuple)
        """
        if len(mode) == 1:  # L, 1
            return (0)
        if len(mode) == 2: # LA, 2
            return (0, 0)
        if len(mode) == 3:  # RGB
            return (0, 0, 0)
        if len(mode) == 4:  # RGBA, CMYK
            return (0, 0, 0, 0)

    def _resizeCanvas(self, image, margins):
        """Resize canvas to include margins.

        Arguments:
            image (obj): PILLOW image.
            margins (list): Margins with shape [mt, mr, mb, ml]

        Returns:
            (obj): The resized PILLOW image.
        """
        width, height = image.size
        mt, mr, mb, ml = margins
        new_width = width + mr + ml
        new_height = height + mt + mb
        mode = image.mode
        result = Image.new(mode, (new_width, new_height), self._getBackground(mode))
        result.paste(image, (ml, mt))
        return result

    def _calcMargins(self, wall_size, size, position):
        """Calculate margins according to image dimensions and the desired position and dimensions of the watermark.

        Arguments:
            wall_size (tuple): Image size.
            size (tuple): Watermark size.
            position (str): Watermark position (one of 'topleft', 'topright', 'bottomright', 'bottomleft' or 'center').

        Raises:
            ValueError: Raised when position is not recognized.
        """
        possible_positions = ['topleft', 'topright', 'bottomright', 'bottomleft', 'center']
        if position not in possible_positions:
            raise ValueError('Position could be one of %s.' % (', '.join(possible_positions)))
        if 'left' in position:
            ml = 0
            mr = wall_size[0] - size[0]
        elif 'right' in position:
            ml = wall_size[0] - size[0]
            mr = 0
        else:
            ml = mr = round((wall_size[0] - size[0])/2)
        if 'top' in position:
            mt = 0
            mb = wall_size[1] - size[1]
        elif 'bottom' in position:
            mt = wall_size[1] - size[1]
            mb = 0
        else:
            mt = mb = round((wall_size[1] - size[1])/2)
        return (mt, mr, mb, ml)

    def prepareWatermark(self, wm_file, to_gray=True, fit='width', position='center', distance=(None, None)):
        """Prepare the Watermark according to desired fit, position and the raster file.

        Arguments:
            wm_file (str): The path to the watermark.

        Keyword Arguments:
            to_gray (bool): Whether to grayscale the watermark (default: {True})
            fit (str): How to fit the watermark (one of 'height', 'width', 'stretch', 'original'; default: {'width'})
            position (str): Position of the watermark (one of 'topleft', 'topright', 'bottomright', 'bottomleft' or 'center'; default: {'center'})
            distance (tuple): Tuple of shape (distance_x: int, distance_y: int), where distance_x, distance_y the x, y distances in pixels of watermark in tiled mode; ignored when `fit` not 'tile'.

        Returns:
            (str): Path to the resized file.

        Raises:
            ValueError: Raised when fit is not recognized or distance out of bounds.
        """
        wm = Image.open(wm_file)
        wm_width, wm_height = wm.size
        src_ds = self.raster
        if (fit == 'stretch'):
            size = (src_ds.RasterXSize, src_ds.RasterYSize)
        elif (fit == 'height'):
            size = (round(wm_width * src_ds.RasterYSize / wm_height), src_ds.RasterYSize)
        elif (fit == 'width'):
            size = (src_ds.RasterXSize, round(wm_height * src_ds.RasterXSize / wm_width))
        elif (fit == 'original'):
            size = wm.size
        elif (fit == 'tile'):
            if not isinstance(distance, tuple) or len(distance) != 2:
                raise ValueError("`distance` should be tuple of shape (distance_x, distance_y).")
            dx, dy = distance
            if dx is None or dy is None or dx >= src_ds.RasterXSize or dy >= src_ds.RasterYSize or dx <= 0 or dy <= 0:
                raise ValueError('`distance` should contain positive x, y distances lower than corresponding raster dimensions.')
            tiled = Image.new(wm.mode, (src_ds.RasterXSize, src_ds.RasterYSize), self._getBackground(wm.mode))
            x, y = dx, dy
            while y < src_ds.RasterYSize:
                tiled.paste(wm, (x, y))
                x += wm_width + dx
                if x > src_ds.RasterXSize:
                    x = x - src_ds.RasterXSize
                    y += wm_height + dy
            if to_gray:
                tiled = tiled.convert('LA')
            tiled_file = self._appendToFilename(wm_file, '-tiled')
            tiled.save(tiled_file)
            return tiled_file
        else:
            raise ValueError('Fit could be one of `stretch`, `height`, `width`, `original`, `tile`.')

        wm = wm.resize(size, Image.ANTIALIAS)
        if (size[0] > src_ds.RasterXSize):
            left = round((size[0] - src_ds.RasterXSize)/2)
            right = src_ds.RasterXSize + left
            wm = wm.crop((left, 0, right, size[1]))
            size = (src_ds.RasterXSize, size[1])
        if (size[1] > src_ds.RasterYSize):
            top = round((size[1] - src_ds.RasterYSize)/2)
            bottom = src_ds.RasterYSize + top
            wm = wm.crop((0, top, size[0], bottom))
            size = (size[0], src_ds.RasterYSize)
        margins = self._calcMargins((src_ds.RasterXSize, src_ds.RasterYSize), size, position)
        src_ds = None
        if to_gray:
            wm = wm.convert('LA')
        wm = self._resizeCanvas(wm, margins)
        resized_file = self._appendToFilename(wm_file, '-resized')
        wm.save(resized_file)
        return resized_file

    def translateWM(self, wm_file, **kwargs):
        """Translate watermark.

        Translation includes resize, change of mode, and spatial translation.

        Arguments:
            wm_file (str): Path to watermark file.
            **kwargs: Additional arguments describing how to fit the watermark (see self.prepareWatermark)

        Returns:
            (str) Path to translated file
        """
        resized = self.prepareWatermark(wm_file, **kwargs)
        src_ds = self.raster
        wm = gdal.Open(resized, gdal.GA_ReadOnly)
        rf = src_ds.GetSpatialRef()
        gcps = src_ds.GetGCPs()
        ulx, xres, xskew, uly, yskew, yres  = src_ds.GetGeoTransform()
        lrx = ulx + (src_ds.RasterXSize * xres)
        lry = uly + (src_ds.RasterYSize * yres)
        translated_file = self._appendToFilename(wm_file, '-translated')
        translated = gdal.Translate(translated_file, wm, outputBounds=[ulx,uly,lrx,lry], GCPs=gcps, outputSRS=rf)
        translated = None
        wm = None
        return translated_file


    def rgb2pct(self, src_filename, dst_filename, driver, color_count=256):
        """Convert a 24bit RGB image to 8bit paletted.

        From GDAL: https://gdal.org/programs/rgb2pct.html.

        Compute an optimal pseudo-color table for a given RGB image using a median cut algorithm on a downsampled RGB histogram. Then it converts the image into a pseudo-colored image using the color table. This conversion utilizes Floyd-Steinberg dithering (error diffusion) to maximize output image visual quality.

        Arguments:
            src_filename (str): The input RGB file path.
            dst_filename (str): The output path of the pseudo-colored file that will be created.
            driver (str): The driver to open the input RGB file.

        Keyword Arguments:
            color_count (number): The number of colors in the generated color table. Must be between 2 and 256. (default: {256})
        """
        src_ds = gdal.Open(src_filename)
        ct = gdal.ColorTable()
        err = gdal.ComputeMedianCutPCT(src_ds.GetRasterBand(1),
                                       src_ds.GetRasterBand(2),
                                       src_ds.GetRasterBand(3),
                                       color_count, ct,
                                       callback=gdal.TermProgress_nocb)

        # Create the working file.  We have to use TIFF since there are few formats
        # that allow setting the color table after creation.

        if driver.ShortName == 'GTiff':
            tif_filename = dst_filename
        else:
            import tempfile
            tif_filedesc, tif_filename = tempfile.mkstemp(suffix='.tif')

        gtiff_driver = gdal.GetDriverByName('GTiff')

        tif_ds = gtiff_driver.Create(tif_filename,
                                     src_ds.RasterXSize, src_ds.RasterYSize, 1)

        tif_ds.GetRasterBand(1).SetRasterColorTable(ct)

        # ----------------------------------------------------------------------------
        # We should copy projection information and so forth at this point.

        tif_ds.SetProjection(src_ds.GetProjection())
        tif_ds.SetGeoTransform(src_ds.GetGeoTransform())
        if src_ds.GetGCPCount() > 0:
            tif_ds.SetGCPs(src_ds.GetGCPs(), src_ds.GetGCPProjection())

        # ----------------------------------------------------------------------------
        # Actually transfer and dither the data.

        err = gdal.DitherRGB2PCT(src_ds.GetRasterBand(1),
                                 src_ds.GetRasterBand(2),
                                 src_ds.GetRasterBand(3),
                                 tif_ds.GetRasterBand(1),
                                 ct,
                                 callback=gdal.TermProgress_nocb)

        tif_ds = None

        if tif_filename != dst_filename:
            tif_ds = gdal.Open(tif_filename)
            driver.CreateCopy(dst_filename, tif_ds)
            tif_ds = None

            os.close(tif_filedesc)
            gtiff_driver.Delete(tif_filename)


    def embed_image(self, watermark, output_img, transparency=1., **kwargs):
        """Embed a watermark in the raster.

        The watermark is transformed accordingly to the placement pareameters and embedded to the raster.

        Arguments:
            watermark (str): Path of the watermark image.
            output_img (str): Path of the output watermarked file.
            **kwargs: Additional arguments describing how to fit the watermark (see self.prepareWatermark)

        Keyword Arguments:
            transparency (float): Transparency of the watermark (default: {1.})
        """
        raster = self.raster
        driver = self.driver

        mode = self.mode
        bandInterp = self.band_interpretation

        translated_file = self.translateWM(watermark, **kwargs)
        wm = gdal.Open(translated_file)
        wm_mode, wm_bandInterp = self.getBandInterpretation(wm)
        merged = driver.CreateCopy(output_img, raster)

        for color in bandInterp.keys():
            band = raster.GetRasterBand(bandInterp[color])
            stats = band.GetStatistics(False, True)
            max_value = stats[1]
            raster_arr = band.ReadAsArray()
            noDataValue = band.GetNoDataValue()
            wm_arr = wm.GetRasterBand(wm_bandInterp[color]).ReadAsArray()
            wm_alpha_arr = wm.GetRasterBand(wm_bandInterp['Alpha']).ReadAsArray()
            threshold = 0.1
            if color == 'Alpha':
                max_alpha = round(stats[2] + stats[3])
            for i in range(len(raster_arr)):
                for j in range(len(raster_arr[i])):
                    wm_value = wm_arr[i][j]/255
                    alpha = wm_alpha_arr[i][j]/255
                    if wm_value*alpha > threshold:
                        if color == 'Alpha':
                            if raster_arr[i][j] == noDataValue or raster_arr[i][j] == 0:
                                raster_arr[i][j] = max_alpha
                            continue
                        alpha = alpha*transparency
                        norm_value = (1 - wm_value)*alpha
                        if raster_arr[i][j] != noDataValue:
                            true_value = raster_arr[i][j]/max_value
                            raster_arr[i][j] = round((1 - (1 - true_value)*(1 - alpha) - norm_value)*max_value)
                        else:
                            raster_arr[i][j] = round((1 - norm_value)*max_value)
            merged.GetRasterBand(bandInterp[color]).WriteArray(raster_arr)
        merged = None
        if self.paletteCount is not None:
            rgb2pct(output_img, output_img, driver, color_count=self.paletteCount)
        self._embedded = output_img


    def show(self, external=False):
        """Show the embedded image.

        Keyword Arguments:
            external (bool): Whether to show the image externally (default: {False})

        Returns:
            (PIL.Image): The Pillow image object
        """
        if self._embedded is None:
            return None
        img = Image.open(self._embedded)
        if external:
            img.show()
        return img


    def _get_color_bands_no(self):
        """Return band numbers with bands containing colors (not transparency).

        Returns:
            (list): List of band numbers.
        """
        if self.mode == 'grayscale':
            bands = [self.band_interpretation['Gray']]
        else:
            bands = []
            for color in ['Red', 'Green', 'Blue']:
                bands.append(self.band_interpretation[color])
        return bands

    def embed_message(self, output_img, message):
        """Embed an invisible message to raster.

        Arguments:
            output_img (str): Path of the output image.
            message (str): Message to embed.
        """
        tif_img = output_img if self.driver.ShortName == 'GTiff' else output_img + '.tif'
        merged = gdal.GetDriverByName('GTiff').CreateCopy(tif_img, self._raster)
        qr = None

        bands = self._get_color_bands_no()
        for band_no in bands:
            band = self._raster.GetRasterBand(band_no)
            merged_band = merged.GetRasterBand(band_no)
            xsize, ysize = np.shape(band.ReadAsArray())
            LL3, (LH3, HL3, HH3), C2, C1 = pywt.wavedec2(band.ReadAsArray(), 'haar', level=3)

            dim = min(np.shape(HH3))
            if qr is None:
                qr = createQR(message, dim)
                qr_values = scramble(np.array(qr), iterations=20)

            alpha = np.mean(np.abs(HH3))
            for x in np.arange(0, dim):
                for y in np.arange(0, dim):
                    HH3[x][y] = HH3[x][y] + alpha if qr_values[x][y] else HH3[x][y] - alpha
            channel = pywt.waverec2((LL3, (LH3, HL3, HH3), C2, C1), 'haar')
            # TODO Check pixel value type?
            # channel = np.array(np.around(channel), dtype='uint8')
            channel = channel[:xsize-1, :ysize-1]
            merged_band.WriteArray(channel)
            merged_band.FlushCache()

        merged = None

        if self.driver.ShortName != 'GTiff':
            tif_ds = gdal.Open(tif_img)
            self.driver.CreateCopy(output_img, tif_ds)
            tif_ds = None

            gdal.GetDriverByName('GTiff').Delete(tif_img)

        if self.paletteCount is not None:
            rgb2pct(output_img, output_img, driver, color_count=self.paletteCount)


    def detect_message(self, file):
        """Detect the invisible message embedded to the file.

        Arguments:
            file (str): Path of the image file.

        Returns:
            (str): The embedded message.
        """
        wm = Watermark(file)
        bitmap = None

        bands = wm._get_color_bands_no()
        for band_no in bands:
            band_wm = wm.raster.GetRasterBand(band_no)
            color = gdal.GetColorInterpretationName(band_wm.GetColorInterpretation())
            try:
                band = self.raster.GetRasterBand(self.band_interpretation[color])
            except KeyError:
                continue
            LL3, (LH3, HL3, HH3), C2, C1 = pywt.wavedec2(band.ReadAsArray(), 'haar', level=3)
            LL3w, (LH3w, HL3w, HH3w), C2, C1 = pywt.wavedec2(band_wm.ReadAsArray(), 'haar', level=3)
            dim = min(np.shape(HH3))
            if bitmap is None:
                bitmap = np.array([np.array([0.]*dim)]*dim)

            alpha = np.mean(np.abs(HH3))
            for x in np.arange(0, dim):
                for y in np.arange(0, dim):
                    try:
                        bitmap[x][y] += (HH3w[x][y] - HH3[x][y])/alpha
                    except IndexError:
                        pass

        if bitmap is None:
            return None
        def arrayToBool(elem):
            return True if elem >= 0 else False
        arrayToBoolVec = np.vectorize(arrayToBool)

        bitmap = unscramble(arrayToBoolVec(bitmap), iterations=20)
        img = Image.fromarray(bitmap)
        try:
            message = decode(img)[0].data.decode()
        except IndexError:
            message = None

        return message
