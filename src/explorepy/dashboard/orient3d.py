
from __future__ import division
import numpy as np
from bokeh.core.properties import Any, Dict, Instance, String
from bokeh.models import ColumnDataSource, LayoutDOM
from bokeh.driving import count
from bokeh.io import curdoc
from bokeh.io import show
from bokeh.util.compiler import TypeScript


# This defines some default options for the Graph3d feature of vis.js
# See: http://visjs.org/graph3d_examples.html for more details. Note
# that we are fixing the size of this component, in ``options``, but
# with additional work it could be made more responsive.
DEFAULTS = {
    'width':          '600px',
    'height':         '600px',
    'style':          'surface',
    'showPerspective': True,
    'showGrid':        True,
    'keepAspectRatio': True,
    'verticalRatio':   1.0,
    'legendLabel':     'stuff',
    'cameraPosition':  {
        'horizontal': -0.35,
        'vertical':    0.22,
        'distance':    1.8,
    }
}


# This custom extension model will have a DOM view that should layout-able in
# Bokeh layouts, so use ``LayoutDOM`` as the base class. If you wanted to create
# a custom tool, you could inherit from ``Tool``, or from ``Glyph`` if you
# wanted to create a custom glyph, etc.
class orient3d(LayoutDOM):

    # The special class attribute ``__implementation__`` should contain a string
    # of JavaScript (or TypeScript) code that implements the JavaScript side
    # of the custom extension model.
    __implementation__ = "orient3d.ts"

    # Below are all the "properties" for this model. Bokeh properties are
    # class attributes that define the fields (and their types) that can be
    # communicated automatically between Python and the browser. Properties
    # also support type validation. More information about properties in
    # can be found here:
    #
    #    https://bokeh.pydata.org/en/latest/docs/reference/core.html#bokeh-core-properties

    # This is a Bokeh ColumnDataSource that can be updated in the Bokeh
    # server by Python code
    data_source = Instance(ColumnDataSource)

    # The vis.js library that we are wrapping expects data for x, y, and z.
    # The data will actually be stored in the ColumnDataSource, but these
    # properties let us specify the *name* of the column that should be
    # used for each field.
    x = String

    y = String

    z = String

    # Any of the available vis.js options for Graph3d can be set by changing
    # the contents of this dictionary.
    options = Dict(String, Any, default=DEFAULTS)

"""
x = np.arange(0, 300, 20)
y = np.arange(0, 300, 20)
xx, yy = np.meshgrid(x, y)
xx = xx.ravel()
yy = yy.ravel()


def compute(t):
    value = np.sin(xx/50 + t/10) * np.cos(yy/50 + t/10) * 50 + 50
    return dict(x=xx, y=yy, z=value)


source = ColumnDataSource(data=compute(0))

surface = orient3d(x="x", y="y", z="z", data_source=source)

curdoc().add_root(surface)


@count()
def update(t):
    source.data = compute(t)


curdoc().add_periodic_callback(update, 100)
curdoc().title = "Surface3d"
show(surface)
"""

"""
x = np.arange(0, 300, 10)
y = np.arange(0, 300, 10)
xx, yy = np.meshgrid(x, y)
xx = xx.ravel()
yy = yy.ravel()
value = np.sin(xx / 50) * np.cos(yy / 50) * 50 + 50

source = ColumnDataSource(data=dict(x=xx, y=yy, z=value))

surface = orient3d(x="x", y="y", z="z", data_source=source, width=600, height=600)

show(surface)
"""
