#!/usr/bin/env python
# -*- coding: utf-8 -*-

##############################################################################
#  Copyright Kitware Inc. and Epidemico Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
##############################################################################
import gaia.formats as formats
import gdal, ogr, os, osr
import numpy as np
import itertools
import geopandas
import sys

from gaia.inputs import GaiaIO
from gaia.gaia_process import GaiaProcess
from gaia_density_computations_plugin import config
from gaia.geo.geo_inputs import RasterFileIO
from skimage.graph import route_through_array
import matplotlib.pyplot as plt
from math import sqrt,ceil


class DensityComputationsProcess(GaiaProcess):

    """
        Density Computations.
    """
    default_output = formats.RASTER

    def __init__(self, **kwargs):
        super(DensityComputationsProcess, self).__init__(**kwargs)

        if not self.output:
            self.output = RasterFileIO(name='result', uri=self.get_outpath())
            self.uri = self.inputs[0]['uri']
            self.resolution = self.inputs[0]['resolution']
            self.outputWidth = self.inputs[0]['outputWidth']
            self.pixelWidth = (360 / self.inputs[0]['pixelWidth'])
            self.pixelHeight = (180 / self.inputs[0]['pixelHeight'])
            self.rasterOrigin = self.inputs[0]['rasterOrigin']

    def calculateDensity(self):


        shpDriver = ogr.GetDriverByName('GeoJSON')

        dataSource = shpDriver.Open(self.uri, 0)

        if dataSource is None:
            print 'Could not open file ' + self.uri
            sys.exit(1)

        if os.path.exists(self.output.uri):
            shpDriver.DeleteDataSource(self.output.uri)
        else:
            self.output.create_output_dir(self.output.uri)

        # Get the layer
        layer = dataSource.GetLayer()

        # open the layer
        # The global bounding box
        xmin = -180.0
        ymin = -90.0
        xmax = 180.0
        ymax = 90.0

        # Number of columns and rows
        nbrColumns = self.resolution['nCol']
        nbrRows = self.resolution['nRow']

        # Caculate the cell size in x and y direction
        csx = (xmax - xmin) / nbrColumns
        csy = (ymax - ymin) / nbrRows

        rows = []
        i = ymax
        while i > ymin:
            j = xmin
            cols = []
            while j < xmax:
                # Set a spatial filter
                layer.SetSpatialFilterRect(j, (i-csy), (j+csx), i)
                # And count the features
                cols.append(layer.GetFeatureCount())
                j += csx
            rows.append(cols)
            i -= csy

        array = np.array(rows)
        reversed_arr = array[::-1]
        ncols = reversed_arr.shape[1]
        nrows = reversed_arr.shape[0]
        originX = self.rasterOrigin[0]
        originY = self.rasterOrigin[1]

        driver = gdal.GetDriverByName('GTiff')
        outRaster = driver.Create(self.output.uri, ncols, nrows, 1, gdal.GDT_Byte)
        outRaster.SetGeoTransform((originX, self.pixelWidth, 0, originY, 0, self.pixelHeight))
        outband = outRaster.GetRasterBand(1)
        outband.WriteArray(reversed_arr)
        outRasterSRS = osr.SpatialReference()
        outRasterSRS.ImportFromEPSG(4326)
        outRaster.SetProjection(outRasterSRS.ExportToWkt())
        outband.FlushCache()

    def compute(self):
        self.calculateDensity()


PLUGIN_CLASS_EXPORTS = [
    DensityComputationsProcess,
]
