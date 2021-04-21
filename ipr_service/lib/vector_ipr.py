import vaex
from vaex.dataframe import DataFrameConcatenated
import geovaex
from geovaex import GeoDataFrame, GeoDataFrameConcatenated
import numpy as np
import pyarrow as pa
import pygeos as pg
import math
from os import getenv


def transform_value(value, seed):
    """Transforms a value in a deterministic way.

    Depending on its type, a value is transformed keeping its shape. Non-numeric parts remain the same, numeric parts change with the same number of digits.

    Arguments:
        value (int|float|str): the original value to be transformed.
        seed (int): Seed for the random state.

    Returns:
        (int|float|str): The transformed value.
    """
    import re
    rs = np.random.RandomState(seed=seed)
    if isinstance(value, int) or isinstance(value, np.int64):
        nod = len(str(value))
        return rs.randint(10**(nod-1), 10**nod)
    if isinstance(value, float):
        transformed = str(transform_value(int(str(value).replace('.', '')), seed=seed))
        dec_pos = str(value).find('.')
        return float(transformed[:dec_pos]+'.'+transformed[dec_pos:])
    if isinstance(value, str):
        pattern = re.compile('([1-9][0-9]*)')
        matches = pattern.findall(value)
        for i, match in enumerate(matches):
            transformed = str(transform_value(int(match), seed=seed+i))
            value = value.replace(match, transformed)
        return value


def _round(value, sample):
    """Rounds a value with number of significant digits extracted from the sample.

    The number of significant digits is determined as the maximum number of significant digits in the number in the sample.

    Arguments:
        value (float): The value to be rounded.
        sample (list): List of floats.

    Returns:
        (float): The rounded value.
    """
    from decimal import Decimal
    precision = abs(min([Decimal(str(number)).as_tuple().exponent for number in sample]))
    return round(value, precision)


@vaex.register_dataframe_accessor('ipr', override=True)
class Ipr(object):
    """Adds Intelectual Property Rights protection capabilities to vaex DataFrames.

    Use cases:
    1. Add fictitious entries in a dataset.
    2. Add points in complex geometries without affecting their shape.

    Fictitious information is added in deterministic way, so that it is possible to confirm that a dataset has been marked.

    Variables:
        N (int): Add one entry for every N records.
        nmin (int): Minimun number of records. Below that, no addition is made.
    """

    N = 1000
    nmin = N/10

    def __init__(self, df):
        """Registered as a vaex DataFrame Accessor.

        Arguments:
            df (vaex.DataFrame|geovaex.GeoDataFrame): DataFrame
        """
        self._df = df
        self._has_geometry = isinstance(df, GeoDataFrame)
        self._ordered_columns = None
        self.__key = None
        # self.__random_state = None


    def set_secret_key(self, key):
        """Set the secret key.

        Arguments:
            key (str): Secret key.
        """
        self.__key = key


    # def __get_random_state(self):
    #     if self.__random_state is None


    def _random_state(self, uuid):
        """Generates the random state.

        Generates a random state combining a UUID with the secret key.

        Arguments:
            uuid (str): UUID

        Returns:
            (np.RandomState): Random State

        Raises:
            InitializeException: When secret key has not been set.
        """
        from hashlib import sha512
        key = getenv('SECRET_KEY', default=self.__key)
        if key is None:
            raise InitializeException("Secret key has not been set, call `Ipr.set_secret_key` first.")
        m = sha512()
        m.update(uuid.encode())
        m.update(key.encode())
        seed = int(m.hexdigest(), 16)
        random_seed = np.random.MT19937(np.random.SeedSequence(seed))
        return np.random.RandomState(seed=random_seed)


    def _order_columns_by_sparsity(self, sample_length=10000, recalculate=False):
        """Orders columns according to their sparsity in descending order.

        Computes how sparse are column values and returns the column names ordered by this value. Only sample of the dataset is used for the computation.

        Keyword Arguments:
            sample_length (int): The length of the sample used to compute sparsity (default: {10000})
            recalculate (bool: If True, the sparsity will be recalculated. By default, a cached value will be returned if already computed (default: {False})

        Returns:
            (list): List of column names.
        """
        if not recalculate and self._ordered_columns is not None:
            return self._ordered_columns
        df = self._df.copy()
        df = df.sample(n=sample_length) if sample_length < len(df) else df
        columns = df.get_column_names(virtual=False)
        sparsity = {}
        for col in columns:
            nunique = df[col].nunique()
            sparsity[col] = nunique/df[col].count()
        sparsity = dict(sorted(sparsity.items(), key=lambda item: item[1], reverse=True))

        sparsity = list(sparsity.keys())
        self._ordered_columns = sparsity

        return sparsity


    def _random_float(self, rs, a, b):
        """Computes a random float in given limits.

        Arguments:
            rs (numpy.RandomState): Random State
            a (float): Lower or Upper limit
            b (float): Upper or Lower limit

        Returns:
            (float): The random number.
        """
        if a == b:
            return a
        if a > b:
            a, b = b, a
        return rs.random_sample()*(b - a) + a


    def create_random_row(self, rand_map):
        """Creates a random row, combining details from the dataset, according to a map.

        Arguments:
            rand_map (list): List with random numbers.

        Returns:
            (vaex.DataFrame, geovaex.GeoDataFrame): A DataFrame with the one random row.
        """
        df = self._df
        cols = df.get_column_names()
        kwargs = {}
        new = vaex.from_arrays()
        for i, col in enumerate(cols):
            idx = int(rand_map[i])
            value = transform_value(df[idx][i], rand_map[i])
            new.add_column(col, np.array([value]))
        if self._has_geometry:
            idx = rand_map[-1]
            geometry = self._df.geometry[idx:idx+1]
            new = geovaex.from_df(geometry=geometry, df=new)
        return new


    def get_random_rows(self, uuid):
        """Creates random rows.

        Creates N random rows, combining details from the dataset, in a deterministic way using the uuid value.

        Arguments:
            uuid (str): UUID

        Returns:
            list: A list of DataFrames, with one random row each.
        """
        N = self.N
        nmin = self.nmin
        df = self._df.copy()
        rs = self._random_state(uuid)
        rows = []
        parts = math.ceil(len(df)/N)
        for i in range(0, parts):
            lower = i*N
            upper = min((i+1)*N, len(df))
            if upper - lower < nmin:
                continue
            size = len(df.get_column_names())
            if self._has_geometry:
                size += 1
            rand_map = rs.randint(lower, upper, size=size)
            rows.append(self.create_random_row(rand_map))
        return rows


    def get_random_geometries(self, rs):
        """Get random geometries, using a random state.

        The geometries are chosen from a subset containing only linestrings, polygons, multilinestrings and multipolygons.

        Arguments:
            rs (numpy.RandomState): Random State

        Returns:
            (tuple): A tuple of indices and geometries.
        """
        multiplier = 10
        df = self._df
        indices = np.flatnonzero(df.predicates.has_type([1,3,5,6]).to_numpy())
        N = math.ceil(len(indices) / self.N)*multiplier
        rand_map = rs.randint(0, len(indices), size=N)
        indices = np.unique(indices.take(rand_map))
        indices.sort()
        geometries = df.geometry.take(indices)

        return (indices, geometries)


    def random_indices(self):
        """Get random indices evenly distributed in the dataframe.

        Returns:
            (list): List of indices
        """
        N = self.N
        nmin = self.nmin
        df = self._df
        idxs = []
        parts = math.ceil(len(df)/N)
        for i in range(0, parts):
            lower = i*N
            upper = min((i+1)*N, len(df))
            if upper - lower < nmin:
                continue
            idxs.append(np.random.randint(lower, upper))

        return idxs


    def transform_geometry(self, geom, rs, max_points=5):
        """Transforms a geometry embedding new points.

        In case geom is (multi)line or (multi)polygon, it adds points collinear to their neighbours, so that an equivalent geometry is generated. The number of extra points depends on the number of vertices in the geometry.

        Arguments:
            geom (pygeos.Geometry): Geometry
            rs (numpy.RandomState): Random State
            max_points (int): Maximum value of extra points.

        Returns:
            (pygeos.Geometry)

        Raises:
            ValueError: When geometry type is not supported.
        """
        type_ = pg.get_type_id(geom)
        if type_ == 1 or type_ == 3:
            # LINESTRING or POLYGON
            vertices = pg.get_coordinates(geom)
            size = min(max_points, math.ceil(len(vertices)/6))
            vert_ids = rs.randint(1, len(vertices), size)
            vert_ids.sort()
            new = []
            for idx in vert_ids:
                xa, ya = vertices[idx-1]
                xb, yb = vertices[idx]
                if xa == xb:
                    x = xa
                    y = self._random_float(rs, ya, yb)
                else:
                    x = self._random_float(rs, xa, xb)
                    y = (yb - ya)*(x - xa)/(xb - xa) + ya
                x = _round(x, [xa, xb])
                y = _round(y, [ya, yb])
                new.append((idx, [x, y]))
            offset = 0
            extended = []
            for idx, entry in new:
                extended.extend(vertices[offset:idx])
                extended.append(entry)
                offset = idx
            extended.extend(vertices[offset:])
            extended = np.array(extended)
            result = pg.linestrings(extended) if type_ == 1 else pg.polygons(extended)
        elif type_ == 5 or type_ == 6:
            # MULTILINESTRING or MULTIPOLYGON
            parts = pg.get_parts(geom)
            part_idx = rs.randint(0, len(parts))
            parts[part_idx] = self.transform_geometry(parts[part_idx], rs)
            result = pg.multilinestrings(parts) if type_ == 5 else pg.multipolygons(parts)
        else:
            raise ValueError('geom should be linestring, polygon, multilinestring, or multipolygon.')

        return result


    def embed_fictitious_entries(self, uuid):
        """Embed fictitious records in a DataFrame.

        Fictitious records are constructed combining data from records in a random but deterministic way, so that their detection is possible. The random state is created using a given uuid and the secret key. The extra records are distributed relatively even across the dataframe, but with random (and not deterministic) positions.

        Arguments:
            uuid (str): UUID

        Returns:
            (vaex.DataFrame|geovaex.GeoDataFrame): Dataframe extended with fictitious records.
        """
        df = self._df
        rows = self.get_random_rows(uuid)
        indices = self.random_indices()
        offset = 0
        dfs = []
        for i, idx in enumerate(indices):
            dfs.append(df[offset:idx].trim())
            dfs.append(rows[i])
            offset = idx
        dfs.append(df[offset:].trim())
        concatenated = GeoDataFrameConcatenated(dfs) if self._has_geometry else DataFrameConcatenated(dfs)

        return concatenated


    def detect_fictitious_entries(self, test, uuid):
        """Checks whether a dataframe originates from this dataframe, marked with fictitious entries.

        Arguments:
            test (vaex.DataFrame|geovaex.GeoDataFrame): The dataframe to be checked.
            uuid (str): UUID

        Returns:
            (bool): True if fictitious entries has been detected, False otherwise.
        """
        rows = self.get_random_rows(uuid)
        for row in rows:
            if test.ipr.row_exists(row):
                return True
        return False


    def row_exists(self, row):
        """Checks whether a row exists in the dataframe.

        It ignores columns that does not exist.

        Arguments:
            row (vaex.DataFrame|geovaex.GeoDataFrame): One row dataframe.

        Returns:
            (bool): True if row found and is unique, False otherwise.
        """
        part = self._df.copy()
        assert len(row) == 1
        columns = self._order_columns_by_sparsity()
        for i, col in enumerate(row.get_column_names()):
            if col not in columns:
                continue
            part = part.filter(part[col]==row[0][i], mode='and')
            if len(part) == 0 or part is None:
                return False
        return len(part) == 1


    def embed_geometries(self, uuid):
        """Embeds geometries with additional points, equivalent to the original.

        Retrieves (multi)lines and (multi)polygons, and increase their vertices with some vertices collinear with their neighbours. The resulted geometries could be detected, but they do not alter the original shapes.

        Arguments:
            uuid (str): UUID

        Returns:
            (geovaex.GeoDataFrame): A new dataframe.
        """
        if not self._has_geometry:
            raise TypeError('Dataframe does not contain geometries.')
        df = self._df
        rs = self._random_state(uuid)
        indices, rand_geoms = self.get_random_geometries(rs)
        offset = 0
        dfs = []
        for i, idx in enumerate(indices):
            dfs.append(df[offset:idx].trim())
            geom = self.transform_geometry(rand_geoms[i], rs)
            row = df[idx:idx+1].to_vaex_df()
            row = geovaex.from_df(row, pa.chunked_array([pa.array([pg.to_wkb(geom)])]), crs=df.geometry.crs)
            dfs.append(row)
            offset = idx + 1
        if idx < len(df):
            dfs.append(df[offset:].trim())

        return GeoDataFrameConcatenated(dfs)


    def detect_geometries(self, test, uuid):
        """Detects if a dataset has originated from this one with the given uuid.

        Arguments:
            test (geovaex.GeoDataFrame): The dataframe to be checked.
            uuid (str): UUID

        Returns:
            (bool): True if fake geometries have been detected, False otherwise.
        """
        assert self._has_geometry
        df = self._df
        rs = self._random_state(uuid)
        indices, rand_geoms = self.get_random_geometries(rs)
        for geom in rand_geoms:
            geom = self.transform_geometry(geom, rs)
            if test.predicates.equals(geom).to_numpy().any():
                return True
        return False


class InitializeException(Exception):
    """Raised when object has not fully initialized."""
