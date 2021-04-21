FROM alpine:3.12 as build-stage-1

RUN apk update && \
  apk add --no-cache gcc g++ musl-dev geos geos-dev proj proj-dev proj-util gdal gdal-dev py3-numpy py3-numpy-dev python3 python3-dev py3-pip \
    py3-psycopg2 py3-setuptools py3-psutil py3-six postgresql-dev git build-base cmake bash boost-dev autoconf zlib-dev flex bison ninja rapidjson gflags

RUN ln -s $(which python3) /usr/bin/python

RUN pip3 install --upgrade pip && \
  pip3 install wheel && \
  pip3 install --no-cache-dir --prefix=/usr/local geoalchemy2==0.8.4 pyproj==2.6.1 pygeos==0.9.0 psycopg2==2.8.4

RUN git clone https://github.com/apache/arrow.git --branch apache-arrow-3.0.0 --single-branch

RUN mkdir /arrow/cpp/build
WORKDIR /arrow/cpp/build

ENV ARROW_BUILD_TYPE=release
ENV ARROW_HOME=/usr/local
ENV PARQUET_HOME=/usr/local

#disable backtrace
RUN sed -i -e '/_EXECINFO_H/,/endif/d' -e '/execinfo/d' ../src/arrow/util/logging.cc

RUN cmake -GNinja \
      -DCMAKE_BUILD_TYPE=$ARROW_BUILD_TYPE \
          -DCMAKE_INSTALL_LIBDIR=lib \
          -DCMAKE_INSTALL_PREFIX=$ARROW_HOME \
          -DARROW_WITH_BZ2=ON \
          -DARROW_WITH_ZLIB=ON \
          -DARROW_WITH_ZSTD=ON \
          -DARROW_WITH_LZ4=ON \
          -DARROW_WITH_SNAPPY=ON \
          -DARROW_WITH_BROTLI=ON \
          -DARROW_PARQUET=on \
          -DARROW_PYTHON=on \
          -DARROW_PLASMA=on \
          -DARROW_BUILD_TESTS=OFF \
          ..
RUN ninja install

ENV PYARROW_CMAKE_GENERATOR=Ninja
ENV PYARROW_WITH_PARQUET=1

RUN pip3 install --no-cache-dir --prefix=/usr/local pyarrow==3.0.0

RUN apk add --no-cache pcre-dev
RUN pip3 install --no-cache-dir --prefix=/usr/local vaex-core==2.0.3

FROM build-stage-1 as build-stage-2
RUN pip3 install --no-cache-dir --prefix=/usr/local PyWavelets==1.1.1

FROM alpine:3.12
ARG VERSION

RUN apk update && \
  apk add --no-cache geos-dev proj-util proj-datumgrid gdal-dev pcre-dev git \
    python3 python3-dev py3-pip py3-psycopg2 py3-setuptools py3-numpy py3-psutil py3-gdal py3-pillow py3-matplotlib py3-six \
    py3-pillow py3-pyzbar

ENV VERSION="${VERSION}"
ENV PYTHON_VERSION="3.8"
ENV PYTHONPATH="/usr/local/lib/python${PYTHON_VERSION}/site-packages"

COPY --from=build-stage-2 /usr/local/ /usr/local/

COPY setup.py requirements.txt requirements-testing.txt ./
RUN pip3 install --upgrade pip && \
  pip3 install wheel && \
  pip3 install git+https://github.com/OpertusMundi/geovaex.git@v0.2.1 && \
  pip3 install --no-cache-dir --prefix=/usr/local -r requirements.txt -r requirements-testing.txt

ENV FLASK_APP="ipr_service" \
    FLASK_ENV="testing" \
    FLASK_DEBUG="false"

COPY run-nosetests.sh /
RUN chmod a+x /run-nosetests.sh
ENTRYPOINT ["/run-nosetests.sh"]
