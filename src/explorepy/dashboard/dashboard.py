# -*- coding: utf-8 -*-
from __future__ import division
import numpy as np
import time
from functools import partial
from threading import Thread
from explorepy.tools import HeartRateEstimator

from bokeh.layouts import widgetbox, row, column
from bokeh.models import ColumnDataSource, ResetTool, PrintfTickFormatter, Panel, Tabs
from bokeh.plotting import figure
from bokeh.server.server import Server
from bokeh.palettes import Colorblind
from bokeh.models.widgets import Select, DataTable, TableColumn, RadioButtonGroup
from bokeh.models import SingleIntervalTicker
#from explorepy.dashboard.orient3d import orient3d
#from explorepy.dashboard.surface3d import Surface3d
from bokeh.core.properties import Any, Dict, Instance, String
from bokeh.models import ColumnDataSource, LayoutDOM
from bokeh.util.compiler import TypeScript
from bokeh.io import curdoc
from tornado import gen
from bokeh.driving import count
from bokeh.io import curdoc
from bokeh.io import show



# This defines some default options for the Graph3d feature of vis.js
# See: http://visjs.org/graph3d_examples.html for more details. Note
# that we are fixing the size of this component, in ``options``, but
# with additional work it could be made more responsive.
DEFAULTS = {
    'width':          '200px',
    'height':         '200px',
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

TS_CODE = """
// This custom model wraps one part of the third-party vis.js library:
//
//     http://visjs.org/index.html
//
// Making it easy to hook up python data analytics tools (NumPy, SciPy,
// Pandas, etc.) to web presentations using the Bokeh server.

import {LayoutDOM, LayoutDOMView} from "models/layouts/layout_dom"
import {ColumnDataSource} from "models/sources/column_data_source"
import {LayoutItem} from "core/layout"
import * as p from "core/properties"

declare namespace vis {
  class Graph3d {
    constructor(el: HTMLElement, data: object, OPTIONS: object)
    setData(data: vis.DataSet): void
  }

  class DataSet {
    add(data: unknown): void
  }
}

// This defines some default options for the Graph3d feature of vis.js
// See: http://visjs.org/graph3d_examples.html for more details.
const OPTIONS = {
  width: '600px',
  height: '600px',
  style: 'surface',
  showPerspective: true,
  showGrid: true,
  keepAspectRatio: true,
  verticalRatio: 1.0,
  legendLabel: 'stuff',
  cameraPosition: {
    horizontal: -0.35,
    vertical: 0.22,
    distance: 1.8,
  },
}
// To create custom model extensions that will render on to the HTML canvas
// or into the DOM, we must create a View subclass for the model.
//
// In this case we will subclass from the existing BokehJS ``LayoutDOMView``
export class Surface3dView extends LayoutDOMView {
  model: Surface3d

  private _graph: vis.Graph3d

  initialize(): void {
    super.initialize()

    const url = "https://cdnjs.cloudflare.com/ajax/libs/vis/4.16.1/vis.min.js"
    const script = document.createElement("script")
    script.onload = () => this._init()
    script.async = false
    script.src = url
    document.head.appendChild(script)
  }

  private _init(): void {
    // Create a new Graph3s using the vis.js API. This assumes the vis.js has
    // already been loaded (e.g. in a custom app template). In the future Bokeh
    // models will be able to specify and load external scripts automatically.
    //
    // BokehJS Views create <div> elements by default, accessible as this.el.
    // Many Bokeh views ignore this default <div>, and instead do things like
    // draw to the HTML canvas. In this case though, we use the <div> to attach
    // a Graph3d to the DOM.
    this._graph = new vis.Graph3d(this.el, this.get_data(), OPTIONS)

    // Set a listener so that when the Bokeh data source has a change
    // event, we can process the new data
    this.connect(this.model.data_source.change, () => {
      this._graph.setData(this.get_data())
    })
  }

  // This is the callback executed when the Bokeh data has an change. Its basic
  // function is to adapt the Bokeh data source to the vis.js DataSet format.
  get_data(): vis.DataSet {
    const data = new vis.DataSet()
    const source = this.model.data_source
    for (let i = 0; i < source.get_length()!; i++) {
      data.add({
        x: source.data[this.model.x][i],
        y: source.data[this.model.y][i],
        z: source.data[this.model.z][i],
      })
    }
    return data
  }

  get child_models(): LayoutDOM[] {
    return []
  }

  _update_layout(): void {
    this.layout = new LayoutItem()
    this.layout.set_sizing(this.box_sizing())
  }
}

// We must also create a corresponding JavaScript BokehJS model subclass to
// correspond to the python Bokeh model subclass. In this case, since we want
// an element that can position itself in the DOM according to a Bokeh layout,
// we subclass from ``LayoutDOM``
export namespace Surface3d {
  export type Attrs = p.AttrsOf<Props>

  export type Props = LayoutDOM.Props & {
    x: p.Property<string>
    y: p.Property<string>
    z: p.Property<string>
    data_source: p.Property<ColumnDataSource>
  }
}

export interface Surface3d extends Surface3d.Attrs {}

export class Surface3d extends LayoutDOM {
  properties: Surface3d.Props

  constructor(attrs?: Partial<Surface3d.Attrs>) {
    super(attrs)
  }

  static initClass() {
    // The ``type`` class attribute should generally match exactly the name
    // of the corresponding Python class.
    this.prototype.type = "Surface3d"

    // This is usually boilerplate. In some cases there may not be a view.
    this.prototype.default_view = Surface3dView

    // The @define block adds corresponding "properties" to the JS model. These
    // should basically line up 1-1 with the Python model class. Most property
    // types have counterparts, e.g. ``bokeh.core.properties.String`` will be
    // ``p.String`` in the JS implementatin. Where the JS type system is not yet
    // as rich, you can use ``p.Any`` as a "wildcard" property type.
    this.define<Surface3d.Props>({
      x:            [ p.String   ],
      y:            [ p.String   ],
      z:            [ p.String   ],
      data_source:  [ p.Instance ],
    })
  }
}
Surface3d.initClass()
"""


# This custom extension model will have a DOM view that should layout-able in
# Bokeh layouts, so use ``LayoutDOM`` as the base class. If you wanted to create
# a custom tool, you could inherit from ``Tool``, or from ``Glyph`` if you
# wanted to create a custom glyph, etc.
class Surface3d(LayoutDOM):

    # The special class attribute ``__implementation__`` should contain a string
    # of JavaScript (or TypeScript) code that implements the JavaScript side
    # of the custom extension model.
    __implementation__ = TypeScript(TS_CODE)

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



EEG_SRATE = 250  # Hz
ORN_SRATE = 20  # Hz
WIN_LENGTH = 10  # Seconds
MODE_LIST = ['EEG', 'ECG']
CHAN_LIST = ['Ch1', 'Ch2', 'Ch3', 'Ch4', 'Ch5', 'Ch6', 'Ch7', 'Ch8']
DEFAULT_SCALE = 10 ** -3  # Volt
N_MOVING_AVERAGE = 60
V_TH = [10**-5, 5 * 10 ** -3]  # Noise threshold for ECG (Volt)
ORN_LIST = ['accX', 'accY', 'accZ', 'gyroX', 'gyroY', 'gyroZ', 'magX', 'magY', 'magZ']

SCALE_MENU = {"1 uV": 6., "5 uV": 5.3333, "10 uV": 5., "100 uV": 4., "500 uV": 3.3333, "1 mV": 3., "5 mV": 2.3333,
              "10 mV": 2., "100 mV": 1.}
TIME_RANGE_MENU = {"10 s": 10., "5 s": 5., "20 s": 20.}

LINE_COLORS = ['green', '#42C4F7', 'red']
FFT_COLORS = Colorblind[8]
ORN3D_LIST = ['x', 'y', 'z']

x = np.arange(-100, 100, 5)
y = np.arange(-100, 100, 5)

xx, yy = np.meshgrid(x, y)

r = np.sqrt((xx - 0)**2 + (yy - 0)**2)
insideC = r < 100

xx = xx[insideC]
yy = yy[insideC]


xx = xx.ravel()
yy = yy.ravel()

"""
xx=0
yy=0
"""



class Dashboard:
    """Explorepy dashboard class"""

    def __init__(self, n_chan):
        self.n_chan = n_chan
        self.y_unit = DEFAULT_SCALE
        self.offsets = np.arange(1, self.n_chan + 1)[:, np.newaxis].astype(float)
        self.chan_key_list = ['Ch' + str(i + 1) for i in range(self.n_chan)]
        self.exg_mode = 'EEG'
        self.rr_estimator = None
        self.win_length = WIN_LENGTH

        # Init ExG data source
        exg_temp = np.zeros((n_chan, 2))
        exg_temp[:, 0] = self.offsets[:, 0]
        exg_temp[:, 1] = np.nan
        init_data = dict(zip(self.chan_key_list, exg_temp))
        init_data['t'] = np.array([0., 0.])
        self.exg_source = ColumnDataSource(data=init_data)

        # Init ECG R-peak source
        init_data = dict(zip(['r_peak', 't'], [np.array([None], dtype=np.double), np.array([None], dtype=np.double)]))
        self.r_peak_source = ColumnDataSource(data=init_data)

        # Init ORN data source
        init_data = dict(zip(ORN_LIST, np.zeros((9, 1))))
        init_data['t'] = [0.]
        self.orn_source = ColumnDataSource(data=init_data)

        # init ORN3D data source
        #init_data = dict(zip(ORN3D_LIST, np.zeros((3, 1))))
        #init_data['t'] = [0.]
        #self.orn3d_source = ColumnDataSource(data=init_data)
        self.orn3d_source = ColumnDataSource(data=self.compute(0))
        self.orn3d_plot = Surface3d(x="x", y="y", z="z", data_source=self.orn3d_source, width=600, height=600)
        #self.orn3d_plot = figure(y_range=(0.01, self.n_chan + 1 - 0.01), y_axis_label='Voltage', x_axis_label='Time (s)',
        #                      title="ExG signal",
        #                       plot_height=600, plot_width=1270,
        #                       y_minor_ticks=int(10),
        #                       tools=[ResetTool()], active_scroll=None, active_drag=None,
        #                       active_inspect=None, active_tap=None)
        # Init table sources
        self.heart_rate_source = ColumnDataSource(data={'heart_rate': ['NA']})
        self.firmware_source = ColumnDataSource(data={'firmware_version': ['NA']})
        self.battery_source = ColumnDataSource(data={'battery': ['NA']})
        self.temperature_source = ColumnDataSource(data={'temperature': ['NA']})
        self.light_source = ColumnDataSource(data={'light': ['NA']})
        self.battery_percent_list = []
        self.server = None

        # Init fft data source
        init_data = dict(zip(self.chan_key_list, np.zeros((self.n_chan, 1))))
        init_data['f'] = np.array([0.])
        self.fft_source = ColumnDataSource(data=init_data)

    def start_server(self):
        """Start bokeh server"""
        self.server = Server({'/': self._init_doc}, num_procs=1)
        self.server.start()

    def start_loop(self):
        """Start io loop and show the dashboard"""
        self.server.io_loop.add_callback(self.server.show, "/")
        self.server.io_loop.start()

    def _init_doc(self, doc):
        self.doc = doc
        self.doc.title = "Explore Dashboard"
        # Create plots
        self._init_plots()

        # Create controls
        m_widgetbox = self._init_controls()

        # Create tabs
        exg_tab = Panel(child=self.exg_plot, title="ExG Signal")
        orn_tab = Panel(child=column([self.acc_plot, self.gyro_plot, self.mag_plot], sizing_mode='fixed'),
                        title="Orientation")
        orn3d_tab = Panel(child=self.orn3d_plot, title="Orientation visualization")
        fft_tab = Panel(child=self.fft_plot, title="Spectral analysis")
        self.tabs = Tabs(tabs=[exg_tab, orn_tab, fft_tab, orn3d_tab], width=1200)
        # self.tabs = Tabs(tabs=[orn3d_tab], width=1200)
        # self.doc.add_root(self.tabs)
        self.doc.add_root(row([m_widgetbox, column([self.tabs])]))

        #curdoc().add_root(self.orn3d_plot)
        self.doc.add_periodic_callback(self._update_fft, 2000)
        self.doc.add_periodic_callback(self._update_heart_rate, 2000)
        #self.doc.add_periodic_callback(self.update_orn3d, 1000)


    @gen.coroutine
    def update_exg(self, time_vector, ExG):
        """update_exg()
        Update ExG data in the visualization

        Args:
            time_vector (list): time vector
            ExG (np.ndarray): array of new data

        """
        # Update ExG data
        ExG = self.offsets + ExG / self.y_unit
        new_data = dict(zip(self.chan_key_list, ExG))
        new_data['t'] = time_vector
        self.exg_source.stream(new_data, rollover=2 * EEG_SRATE * WIN_LENGTH)

    @gen.coroutine
    def update_orn(self, timestamp, orn_data):
        """Update orientation data

        Args:
            timestamp (float): timestamp of the sample
            orn_data (float vector): Vector of orientation data with shape of (9,)
        """
        new_data = dict(zip(ORN_LIST, np.array(orn_data)[:, np.newaxis]))
        new_data['t'] = [timestamp]
        self.orn_source.stream(new_data, rollover=2 * WIN_LENGTH * ORN_SRATE)

    def compute(self, t):
        value = (np.cos(xx / 200 ) * np.cos(yy / 200 )) * np.exp((xx**2+yy**2)*(-0.001)) + 50
        return dict(x=xx, y=yy, z=value)


    @gen.coroutine
    def update_orn3d(self, timestamp):
        self.orn3d_source.data = self.compute(timestamp)
        """
        new_data = dict(zip(ORN3D_LIST, np.array(orn3d_data)[:, np.newaxis]))
        new_data['t'] = [timestamp]
        self.orn3d_source.stream(new_data, rollover=2 * WIN_LENGTH * ORN_SRATE)
        """

    @gen.coroutine
    def update_info(self, new):
        """Update device information in the dashboard

        Args:
            new(dict): Dictionary of new values

        """
        for key in new.keys():
            data = {key: new[key]}
            if key == 'firmware_version':
                self.firmware_source.stream(data, rollover=1)
            elif key == 'battery':
                self.battery_percent_list.append(new[key][0])
                if len(self.battery_percent_list) > N_MOVING_AVERAGE:
                    del self.battery_percent_list[0]
                value = int(np.mean(self.battery_percent_list) / 5) * 5
                if value < 1:
                    value = 1
                self.battery_source.stream({key: [value]}, rollover=1)
            elif key == 'temperature':
                self.temperature_source.stream(data, rollover=1)
            elif key == 'light':
                data[key] = [int(data[key][0])]
                self.light_source.stream(data, rollover=1)
            else:
                print("Warning: There is no field named: " + key)

    @gen.coroutine
    def _update_fft(self):
        """ Update spectral frequency analysis plot
        """
        # Check if the tab is active and if EEG mode is active
        if (self.tabs.active != 2) or (self.exg_mode != 'EEG'):
            return

        exg_data = np.array([self.exg_source.data[key] for key in self.chan_key_list])

        # Check if the length of data is enough for FFT
        if exg_data.shape[1] < EEG_SRATE * 4.5:
            return
        fft_content, freq = get_fft(exg_data)
        data = dict(zip(self.chan_key_list, fft_content))
        data['f'] = freq
        self.fft_source.data = data

    @gen.coroutine
    def _update_heart_rate(self):
        """Detect R-peaks and update the plot and heart rate"""
        if self.exg_mode == 'EEG':
            self.heart_rate_source.stream({'heart_rate': ['NA']}, rollover=1)
            return
        if self.rr_estimator is None:
            self.rr_estimator = HeartRateEstimator()
            # Init R-peaks plot
            self.exg_plot.circle(x='t', y='r_peak', source=self.r_peak_source,
                                 fill_color="red", size=8)

        ecg_data = (np.array(self.exg_source.data['Ch1'])[-500:] - self.offsets[0]) * self.y_unit
        time_vector = np.array(self.exg_source.data['t'])[-500:]

        # Check if the peak2peak value is bigger than threshold
        if (np.ptp(ecg_data) < V_TH[0]) or (np.ptp(ecg_data) > V_TH[1]):
            print("P2P value larger or less than threshold!")
            return

        peaks_time, peaks_val = self.rr_estimator.estimate(ecg_data, time_vector)
        peaks_val = (np.array(peaks_val)/self.y_unit) + self.offsets[0]
        if peaks_time:
            data = dict(zip(['r_peak', 't'], [peaks_val, peaks_time]))
            self.r_peak_source.stream(data, rollover=50)

        # Update heart rate cell
        estimated_heart_rate = self.rr_estimator.heart_rate
        data = {'heart_rate': [estimated_heart_rate]}
        self.heart_rate_source.stream(data, rollover=1)

    @gen.coroutine
    def _change_scale(self, attr, old, new):
        """Change y-scale of ExG plot"""
        new, old = SCALE_MENU[new], SCALE_MENU[old]
        old_unit = 10 ** (-old)
        self.y_unit = 10 ** (-new)

        for ch, value in self.exg_source.data.items():
            if ch in CHAN_LIST:
                temp_offset = self.offsets[CHAN_LIST.index(ch)]
                self.exg_source.data[ch] = (value - temp_offset) * (old_unit / self.y_unit) + temp_offset
        self.r_peak_source.data['r_peak'] = (np.array(self.r_peak_source.data['r_peak'])-self.offsets[0]) *\
                                            (old_unit / self.y_unit) + self.offsets[0]
        print(self.r_peak_source.data['r_peak'].shape, self.r_peak_source.data['t'].shape)


    @gen.coroutine
    def _change_t_range(self, attr, old, new):
        """Change time range"""
        self._set_t_range(TIME_RANGE_MENU[new])

    @gen.coroutine
    def _change_mode(self, new):
        """Set EEG or ECG mode"""
        self.exg_mode = MODE_LIST[new]

    def _init_plots(self):
        """Initialize all plots in the dashboard"""
        self.exg_plot = figure(y_range=(0.01, self.n_chan + 1 - 0.01), y_axis_label='Voltage', x_axis_label='Time (s)',
                               title="ExG signal",
                               plot_height=600, plot_width=1270,
                               y_minor_ticks=int(10),
                               tools=[ResetTool()], active_scroll=None, active_drag=None,
                               active_inspect=None, active_tap=None)

        self.mag_plot = figure(y_axis_label='Magnetometer [mgauss/LSB]', x_axis_label='Time (s)',
                               plot_height=230, plot_width=1270,
                               tools=[ResetTool()], active_scroll=None, active_drag=None,
                               active_inspect=None, active_tap=None)
        self.acc_plot = figure(y_axis_label='Accelerometer [mg/LSB]',
                               plot_height=190, plot_width=1270,
                               tools=[ResetTool()], active_scroll=None, active_drag=None,
                               active_inspect=None, active_tap=None)
        self.acc_plot.xaxis.visible = False
        self.gyro_plot = figure(y_axis_label='Gyroscope [mdps/LSB]',
                                plot_height=190, plot_width=1270,
                                tools=[ResetTool()], active_scroll=None, active_drag=None,
                                active_inspect=None, active_tap=None)
        self.gyro_plot.xaxis.visible = False

        self.fft_plot = figure(y_axis_label='Amplitude (uV)', x_axis_label='Frequency (Hz)', title="FFT",
                               x_range=(0, 70), plot_height=600, plot_width=1270, y_axis_type="log")


        """
        self.orn3d_plot = figure(y_axis_label='Magnetometer [mgauss/LSB]', x_axis_label='Time (s)',
                               plot_height=600, plot_width=1270,
                               tools=[ResetTool()], active_scroll=None, active_drag=None,
                               active_inspect=None, active_tap=None)
                               """

        # Set yaxis properties
        self.exg_plot.yaxis.ticker = SingleIntervalTicker(interval=1, num_minor_ticks=10)

        # Initial plot line
        for i in range(self.n_chan):
            self.exg_plot.line(x='t', y=CHAN_LIST[i], source=self.exg_source,
                               line_width=1.5, alpha=.9, line_color="#42C4F7")
            self.fft_plot.line(x='f', y=CHAN_LIST[i], source=self.fft_source, legend=CHAN_LIST[i] + " ",
                               line_width=2, alpha=.9, line_color=FFT_COLORS[i])
        for i in range(3):
            self.acc_plot.line(x='t', y=ORN_LIST[i], source=self.orn_source, legend=ORN_LIST[i] + " ",
                               line_width=1.5, line_color=LINE_COLORS[i], alpha=.9)
            self.gyro_plot.line(x='t', y=ORN_LIST[i + 3], source=self.orn_source, legend=ORN_LIST[i + 3] + " ",
                                line_width=1.5, line_color=LINE_COLORS[i], alpha=.9)
            self.mag_plot.line(x='t', y=ORN_LIST[i + 6], source=self.orn_source, legend=ORN_LIST[i + 6] + " ",
                               line_width=1.5, line_color=LINE_COLORS[i], alpha=.9)
        """
           self.orn3d_plot.line(x='t', y=ORN3D_LIST[i], source=self.orn3d_source, legend=ORN3D_LIST[i] + " ",
                               line_width=1.5, line_color=LINE_COLORS[i], alpha=.9) 
        """

        # Set x_range
        self.plot_list = [self.exg_plot, self.acc_plot, self.gyro_plot, self.mag_plot]
        self._set_t_range(WIN_LENGTH)

        self.exg_plot.ygrid.minor_grid_line_color = 'navy'
        self.exg_plot.ygrid.minor_grid_line_alpha = 0.05

        # Set the formatting of yaxis ticks' labels
        self.exg_plot.yaxis[0].formatter = PrintfTickFormatter(format="Ch %i")

        # Autohide toolbar/ Legend location
        for plot in self.plot_list:
            plot.toolbar.autohide = True
            plot.background_fill_color = "#fafafa"
            if len(plot.legend) != 0:
                plot.legend.location = "bottom_left"
                plot.legend.orientation = "horizontal"
                plot.legend.padding = 2

    def _init_controls(self):
        """Initialize all controls in the dashboard"""
        # EEG/ECG Radio button
        self.mode_control = RadioButtonGroup(labels=MODE_LIST, active=0)
        self.mode_control.on_click(self._change_mode)

        self.t_range = Select(title="Time window", value="10 s", options=list(TIME_RANGE_MENU.keys()), width=200)
        self.t_range.on_change('value', self._change_t_range)
        self.y_scale = Select(title="Y-axis Scale", value="1 mV", options=list(SCALE_MENU.keys()), width=200)
        self.y_scale.on_change('value', self._change_scale)

        # Create device info tables
        columns = [TableColumn(field='heart_rate', title="Heart Rate (bpm)")]
        self.heart_rate = DataTable(source=self.heart_rate_source, index_position=None, sortable=False,
                                    reorderable=False,
                                    columns=columns, width=200, height=50)

        columns = [TableColumn(field='firmware_version', title="Firmware Version")]
        self.firmware = DataTable(source=self.firmware_source, index_position=None, sortable=False, reorderable=False,
                                  columns=columns, width=200, height=50)

        columns = [TableColumn(field='battery', title="Battery (%)")]
        self.battery = DataTable(source=self.battery_source, index_position=None, sortable=False, reorderable=False,
                                 columns=columns, width=200, height=50)

        columns = [TableColumn(field='temperature', title="Temperature (C)")]
        self.temperature = DataTable(source=self.temperature_source, index_position=None, sortable=False,
                                     reorderable=False, columns=columns, width=200, height=50)

        columns = [TableColumn(field='light', title="Light (Lux)")]
        self.light = DataTable(source=self.light_source, index_position=None, sortable=False, reorderable=False,
                               columns=columns, width=200, height=50)

        # Add widgets to the doc
        m_widgetbox = widgetbox([self.mode_control, self.y_scale, self.t_range, self.heart_rate,
                                 self.battery, self.temperature, self.light, self.firmware], width=200)
        return m_widgetbox

    def _set_t_range(self, t_length):
        """Change time range of ExG and orientation plots"""
        for plot in self.plot_list:
            self.win_length = int(t_length)
            plot.x_range.follow = "end"
            plot.x_range.follow_interval = t_length
            plot.x_range.range_padding = 0.
            plot.x_range.min_interval = t_length


def get_fft(exg):
    """Compute FFT"""
    n_chan, n_sample = exg.shape
    L = n_sample / EEG_SRATE
    n = 1024
    freq = EEG_SRATE * np.arange(int(n / 2)) / n
    fft_content = np.fft.fft(exg, n=n) / n
    fft_content = np.abs(fft_content[:, range(int(n / 2))])
    return fft_content[:, 1:], freq[1:]


if __name__ == '__main__':
    print('Opening Bokeh application on http://localhost:5006/')
    m_dashboard = Dashboard(n_chan=8)
    m_dashboard.start_server()


    def my_loop():
        T = 0
        time.sleep(2)
        while True:
            time_vector = np.linspace(T, T + .2, 50)
            T += .2
            EEG = (np.random.randint(0, 2, (8, 50)) - .5) * .0002  # (np.random.rand(8, 50)-.5) * .0005
            m_dashboard.doc.add_next_tick_callback(partial(m_dashboard.update_exg, time_vector=time_vector, ExG=EEG))

            device_info_attr = ['firmware_version', 'battery', 'temperature', 'light']
            device_info_val = [['2.0.4'], [95], [21], [13]]
            new_data = dict(zip(device_info_attr, device_info_val))
            m_dashboard.doc.add_next_tick_callback(partial(m_dashboard.update_info, new=new_data))

            m_dashboard.doc.add_next_tick_callback(
                partial(m_dashboard.update_orn, timestamp=T, orn_data=np.random.rand(9)))

            m_dashboard.doc.add_next_tick_callback(
                partial(m_dashboard.update_orn3d, timestamp=T))
            time.sleep(0.1)


    thread = Thread(target=my_loop)
    thread.start()
    m_dashboard.start_loop()
