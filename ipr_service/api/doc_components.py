def add_components(spec):
    """Adds the service components to OpenAPI specification.

    Arguments:
        spec (obj): The apispec object.
    """

    # Parameters

    spec.components.parameter('idempotencyKey', 'header', {
        "name": "X-Idempotence-Key",
        "description": "A unique idempotency key assigned to each request.",
        "required": False,
        "schema": {"type": "string"},
        "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    })

    # Schemata

    response = {
        "type": "string",
        "description": "Response type, either *prompt* to initiate the process promptly and wait for the response, either *deferred* to finish the process asynchronously.",
        "enum": ["prompt", "deferred"],
        "default": "deferred"
    }

    vector_base_form = {
        "type": "object",
        "properties": {
            "response": response,
            "original": {
                "type": "string",
                "description": "A resolvable path to the original file, relative to the **input directory**. The file could be in compressed form: zipped or tar(.gz) archive.",
                "example": "/datasets/example.tar.gz"
            },
            "delimiter": {
                "type": "string",
                "description": "In case the file is a delimited text file, the character used to separate values. Ignored for not delimited files.",
                "example": ";",
                "default": ","
            },
            "lat": {
                "type": "string",
                "description": "The attribute name in delimited text files that corresponds to latitude, if the geometry is given in means of lat, lon. Ignored for not delimited files.",
                "example": "latitude"
            },
            "lon": {
                "type": "string",
                "description": "The attribute name in delimited text files that corresponds to longitude, if the geometry is given in means of lat, lon. Ignored for not delimited files.",
                "example": "longitude"
            },
            "geom": {
                "type": "string",
                "description": "The attribute name in delimited text files that corresponds to WKT geometry. Default is 'WKT'; ignored for not delimited files **or** when 'lat', 'lon' are provided.",
                "example": "geometry"
            },
            "crs": {
                "type": "string",
                "description": "The Coordinate Reference System of the geometries. If not given, the CRS information is obtained by the dataset; **required for** spatial files that do not provide CRS information, e.g. CSV.",
                "example": "EPSG:4326"
            },
            "encoding": {
                "type": "string",
                "description": "The encoding of the file. If not given, the encoding is automatically detected.",
                "example": "UTF-8"
            },
        },
    }

    vector_embed_form = {
        **vector_base_form,
        "properties": {
            **vector_base_form["properties"],
            "key": {
                "type": "string",
                "description": "A unique key to embed in dataset.",
                "example": "09061d7e-3b1a-4a14-bfa5-b65b9ce0412d"
            }
        },
        "required": ["original", "key"]
    }
    spec.components.schema('vectorEmbedForm', vector_embed_form)

    vector_detect_form = {
        **vector_base_form,
        "properties": {
            **vector_base_form["properties"],
            "test": {
                "type": "string",
                "description": "A resolvable path to under detection file, relative to the **input directory**. The file could be in compressed form: zipped or tar(.gz) archive.",
                "example": "detect/example.tar.gz"
            },
            "test_delimiter": {
                "type": "string",
                "description": "**Refers to test file**. In case the file is a delimited text file, the character used to separate values. Ignored for not delimited files. **If not given, the value for the original file will be assumed.**",
                "example": ";",
            },
            "test_lat": {
                "type": "string",
                "description": "**Refers to test file**. The attribute name in delimited text files that corresponds to latitude, if the geometry is given in means of lat, lon. Ignored for not delimited files. **If not given, the value for the original file will be assumed.**",
                "example": "latitude"
            },
            "test_lon": {
                "type": "string",
                "description": "**Refers to test file**. The attribute name in delimited text files that corresponds to longitude, if the geometry is given in means of lat, lon. Ignored for not delimited files. **If not given, the value for the original file will be assumed.**",
                "example": "longitude"
            },
            "test_geom": {
                "type": "string",
                "description": "**Refers to test file**. The attribute name in delimited text files that corresponds to WKT geometry. Default is 'WKT'; ignored for not delimited files **or** when 'lat', 'lon' are provided. **If not given, the value for the original file will be assumed.**",
                "example": "geometry"
            },
            "test_crs": {
                "type": "string",
                "description": "**Refers to test file**. The Coordinate Reference System of the geometries. If not given, the CRS information is obtained by the dataset; **required for** spatial files that do not provide CRS information, e.g. CSV. **If not given, the value for the original file will be assumed.**",
                "example": "EPSG:4326"
            },
            "test_encoding": {
                "type": "string",
                "description": "**Refers to test file**. The encoding of the file. If not given, the encoding is automatically detected. **If not given, the value for the original file will be assumed.**",
                "example": "UTF-8"
            },
            "keys": {
                "type": "array",
                "description": "List of keys to detect IPR.",
                "items": {
                    "type": "string",
                    "description": "Embedded key",
                },
                "example": ["09061d7e-3b1a-4a14-bfa5-b65b9ce0412f", "09061d7e-3b1a-4a14-bfa5-b65b9ce0412d", "09061d7e-3b1a-4a14-bfa5-b65b9ce0412e"]
            }
        },
        "required": ["original", "test", "keys"]
    }
    spec.components.schema('vectorDetectForm', vector_detect_form)

    raster_base_form = {
        "type": "object",
        "properties": {
            "response": response,
            "raster": {
                "type": "string",
                "description": "A resolvable path to the raster file, relative to the **input directory**. The file could be in compressed form: zipped or tar(.gz) archive.",
                "example": "rasters/example.tif"
            }
        }
    }

    raster_embed_message_form = {
        **raster_base_form,
        "properties": {
            **raster_base_form["properties"],
            "message": {
                "type": "string",
                "description": "Message to invisible embed in raster.",
                "example": "09061d7e-3b1a-4a14-bfa5-b65b9ce0412d"
            }
        },
        "required": ["raster", "message"]
    }
    spec.components.schema('rasterEmbedMessageForm', raster_embed_message_form)

    raster_detect_form = {
        **raster_base_form,
        "properties": {
            **raster_base_form["properties"],
            "watermarked": {
                "type": "string",
                "description": "A resolvable path to the *watermarked* raster file, relative to the **input directory**. The file could be in compressed form: zipped or tar(.gz) archive.",
                "example": "rasters/example-watermarked.tif"
            }
        },
        "required": ["raster", "watermarked"]
    }
    spec.components.schema('rasterDetectForm', raster_detect_form)

    raster_embed_watermark_form = {
        **raster_base_form,
        "properties": {
            **raster_base_form["properties"],
            "watermark": {
                "type": "string",
                "description": "A resolvable path to the *watermark* that will be embedded to raster, relative to the **input directory**. The file could be in compressed form: zipped or tar(.gz) archive.",
                "example": "logo.png"
            },
            "crs": {
                "type": "string",
                "description": "The Coordinate Reference System of the geometries. If not given, the CRS information is obtained by the dataset; **required for** spatial files that do not provide CRS information, e.g. CSV.",
                "example": "EPSG:4326"
            },
            "transparency": {
                "type": "number",
                "format": "float",
                "default": 1.0,
                "description": "The transparency of the embedded watermark.",
                "minimum": 0.0,
                "maximum": 1.0
            },
            "fit": {
                "type": "string",
                "description": "Fit type of watermark embedding.",
                "enum": ["stretch", "height", "width", "original", "tile"],
                "default": "width"
            },
            "position": {
                "type": "string",
                "description": "Position of watermark embedding.",
                "enum": ["topleft", "topright", "bottomright", "bottomleft", "center"],
                "default": "center"
            },
            "distance_x": {
                "type": "integer",
                "description": "**For *tile* fit.** Horizontal distance in pixels of the watermarks. Ignored when fit is not *tile*; **required** when fit is *tile.",
                "example": 100
            },
            "distance_y": {
                "type": "integer",
                "description": "**For *tile* fit.** Vertical distance in pixels of the watermarks. Ignored when fit is not *tile*; **required** when fit is *tile.",
                "example": 200
            }
        },
        "required": ["raster", "watermark"]
    }
    spec.components.schema('rasterEmbedWatermarkForm', raster_embed_watermark_form)

    # Responses

    validation_error_response = {
        "description": "Form validation error.",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "description": "The key is the request body key.",
                    "additionalProperties": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "Description of validation error."
                        }
                    },
                    "example": {
                        "crs": [
                            "Field must be a valid CRS."
                        ]
                    }
                }
            }
        }
    }
    spec.components.response('validationErrorResponse', validation_error_response)

    spec.components.response('deferredResponse', {
        "description": "Request accepted for process.",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "Request type.",
                            "enum": ["prompt", "deferred"],
                            "example": "deferred"
                        },
                        "ticket": {
                            "type": "string",
                            "description": "The unique ticket assigned to the request.",
                            "example": "caff960ab6f1627c11b0de3c6406a140"
                        },
                        "statusUri": {
                            "type": "string",
                            "description": "The URI to poll for the status of the request.",
                            "example": "/jobs/status?ticket=caff960ab6f1627c11b0de3c6406a140"
                        }
                    }
                }
            }
        }
    })

    spec.components.response('promptEmbedResponse', {
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "description": "When form parameter *download* was set to false.",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "Request type.",
                            "enum": ["prompt", "deferred"]
                        },
                        "path": {
                            "type": "string",
                            "description": "The relative to the *output directory* path for the spatial file.",
                            "example": "2103/3ba6a8b5ecea27db3c5f4e0159c63283/example.csv.gz"
                        }
                    }
                }
            }
        }
    })

    spec.components.response('promptDetectResponse', {
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "description": "When form parameter *download* was set to false.",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "Request type.",
                            "enum": ["prompt", "deferred"]
                        },
                        "key": {
                            "type": "string",
                            "description": "The detected key; null if none detected.",
                            "example": "09061d7e-3b1a-4a14-bfa5-b65b9ce0412d"
                        }
                    }
                }
            }
        }
    })

