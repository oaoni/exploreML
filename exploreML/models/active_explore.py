import numpy as np
import pandas as pd
import seaborn as sns
from bokeh.io import output_notebook, show, save
from bokeh.plotting import figure, Figure, output_file, show, reset_output
from bokeh.layouts import column, row
from bokeh.models import ColorBar, LinearColorMapper, BasicTicker,\
CustomJS, ColumnDataSource, Toggle, Slider, RadioButtonGroup, Select, Legend,\
ColorPicker, Panel, Tabs, RangeSlider, FixedTicker, Select, LinearColorMapper
from bokeh.palettes import all_palettes
from scipy.cluster.hierarchy import linkage, dendrogram

with open('exploreML/exploreML/models/active_explore_js/slider_callback.js','r') as f:
    slider_callback_js = f.read()

with open('exploreML/exploreML/models/active_explore_js/line_callback.js','r') as f:
    line_callback_js = f.read()

class ActiveExplore:

    """
    Args:
    data_dict:
    sampling_dict:
    is_sym:
    num_line_plots:
    clust_methods:
    init_clust:
    active_x:
    row_coord:
    col_coord:
    name: name
    url: name of output file
    plot_location: location of plots with respect to heatmap ['below','left','right','above']
    """

    def __init__(self, data_dict, sampling_dict, is_sym=True, num_line_plots=2,
                 clust_methods = ['None','ward','average'], init_clust = 'None',
                 active_x='active_iter', batch_col='batch', row_coord = 'row_idx', col_coord = 'col_idx',
                 row_name='dim1', col_name='dim2', val_name='query_value',
                 heatmap_colors = 'default', n_colors=10, inds_colors=[1,2,4,5,6,7,8],
                 color_palette='Category10',plot_size=700,
                 name='active explorer', url='active_explorer.html', plot_location='below'):

        M = data_dict['M']
        S_train = data_dict['S_train'].values
        sampling_names, sampling_dfs = zip(*sampling_dict.items())

        self.name = name
        self.numLinePlots = num_line_plots # Parameter for number of line plots
        self.is_sym = is_sym

        #Output file or output notebook
        output_file(filename=url, title=name)

        # Variables and presets
        meta_vars = dict(rowName=row_name, colName=col_name, valName=val_name,
                         rowCoord=row_coord, colCoord=col_coord) # Metadata for variables
        df_index = M.index
        df_cols = M.columns

        #Colors and palettes
        if isinstance(heatmap_colors, sns.palettes._ColorPalette):
            heatmap_colors = heatmap_colors.as_hex()
        else:
            heatmap_colors = sns.diverging_palette(260, 10, n=256).as_hex()

        #Processing inputs
        marker_size=plot_size/M.shape[0] # Produce appropriate marker size for aspect ratio
        n_samplers = len(sampling_names)
        sampling_titles = {sampler:sampler+' Sampling' for sampler in sampling_names}

        sampler_palette = self._makePalette(color_palette, n_colors, inds_colors)
        sampler_color = dict(zip(sampling_names, sampler_palette[:n_samplers]))

        active_dim = sampling_dfs[0].shape[0]
        if self.is_sym:
            sampling_methods = [self._makeSymAL(sampler, row_coord, col_coord, active_x, batch_col)\
                                for sampler in sampling_dfs]
            symMult = 2
        else:
            sampling_methods = sampling_dfs
            symMult = 1

        self.sampling_methods = sampling_methods

        #Precompute the indices for the different clustering methods
        clust_dict = {method:self._makeClustIndex(M, method) for method in clust_methods}
        self.clust_dict = clust_dict
        #Active learning data
        sampling_data = {sample:self._addIndexCols(df, df_index, df_cols, meta_vars)\
                        for df,sample in zip(sampling_methods,sampling_names)}

        # active_dim = list(sampling_data.values())[0].shape[0]

        samplerCol_meta = pd.concat([sampling_data[sampler].describe().loc[['min','max'],:]\
         for sampler in sampling_names]).describe().to_dict()

        self.samplerCol_meta = samplerCol_meta

        # Column source data of mask for each clustering method
        upper_dict = {method:self._makeGImatrix(self._makeMaskUpper(M.iloc[clust_dict[method][0],clust_dict[method][1]]),meta_vars)\
                   .dropna(axis=0).to_dict(orient='list') for method in clust_methods}

        #Collecting the quantitative columns from the sampling data
        quant_options = sampling_methods[0].describe().columns.to_list()

        line_y_keys = [col for col in quant_options[-self.numLinePlots:]]

        # Make sources
        heat_mapper = LinearColorMapper(palette=heatmap_colors,low=M.values.min(), high=M.values.max())

        #Active learning column source data
        sampling_sources = {sampler:ColumnDataSource(data.to_dict(orient='list'))\
                        for sampler,data in sampling_data.items()}

        upper_source = ColumnDataSource(data=upper_dict[init_clust])

        # Initialize sources
        #GI column source data
        heatmap_source = ColumnDataSource(data=self._makeGImatrix(M, meta_vars).to_dict(orient='list'))
        # Active sources
        active_sources = {sampler:ColumnDataSource({key:[]\
                          for key in sampling_sources[sampler].data.keys()})\
                          for sampler in sampling_names}
        #Training data source
        train_source = ColumnDataSource(self._makeGImatrix(M.where(S_train.astype(bool)), meta_vars)\
        .dropna(axis=0)\
        .to_dict(orient='list'))

        TOOLS = "hover,save,pan,box_zoom,reset,wheel_zoom"
        p = Figure(title="Active Learning Explorer",frame_width=plot_size, frame_height=plot_size,
                   tools=TOOLS, tooltips=[('index', '@{} | @{}'.format(row_name,col_name)),(val_name, '@{}'.format(val_name))],
                   toolbar_location='above', x_range=clust_dict[init_clust][3],y_range=clust_dict[init_clust][2][::-1],
                   output_backend="webgl", match_aspect=True)
        self.clust_dict = clust_dict

        p.grid.grid_line_color = None
        p.axis.axis_line_color = None
        p.axis.major_tick_line_color = None
        p.axis.major_label_text_font_size = "7px"
        p.axis.major_label_standoff = 0
        p.xaxis.major_label_orientation = np.pi/3
        p.xaxis.axis_label = col_name
        p.yaxis.axis_label = row_name

        color_bar = ColorBar(color_mapper=heat_mapper, major_label_text_font_size="8px",
                             location=(0,0), ticker=BasicTicker(),
                             width=15,label_standoff=7)



        self.color_bar = color_bar
        p.add_layout(color_bar, "right")

        mn = color_bar.color_mapper.low.round(1)
        mx = color_bar.color_mapper.high.round(1)

        range_slider = RangeSlider(start=mn, end=mx, value=(mn,mx), step=(mx-mn)/50, title="Colorbar Range")
        range_slider.js_on_change("value", CustomJS(args=dict(cbar=color_bar),code="""
            console.log('range_slider: value=' + this.value, this.toString())

            var range_values = cb_obj.value;
            //window.alert(range_values);

            var low = range_values[0];
            var high = range_values[1];

            cbar.color_mapper.low = low;
            cbar.color_mapper.high = high;

        """))

        colormap_options = ["default", "plasma", "viridis", "magma", "vlag", "coolwarm", "icefire"]
        colormap_dict = {palette:sns.color_palette(palette,n_colors=64).as_hex() for palette in colormap_options[1:]}
        colormap_dict['default'] = heatmap_colors


        select_colorbar = Select(title="Colorbar Palette:", value="default", options=colormap_options)
        select_colorbar.js_on_change("value", CustomJS(args=dict(cbar=color_bar, cmap_dict=colormap_dict),code="""
            console.log('select: value=' + this.value, this.toString())

            //window.alert(cmap_dict[cb_obj.value]);
            cbar.color_mapper.palette = cmap_dict[cb_obj.value];
        """))

        #GI Heatmap
        heatFig = p.rect(x=col_name,y=row_name,height=1,width=1,
               source=heatmap_source,
               color={'field': val_name, 'transform': heat_mapper})
        self.heatmap_source = heatmap_source

        heatFigs = {sampler:p.circle_cross(x=col_name, y=row_name, source=active_sources[sampler],\
                    size=marker_size,color=sampler_color[sampler],line_color=sampler_color[sampler],
                    line_width=0)\
                    for sampler in sampling_names}

        #Training mask
        trainFig = p.square_pin(x=col_name,y=row_name,source=train_source,
                          size=marker_size,color="white")
        trainFig.visible = False

        #Upper mask
        upperFig = p.square(x=col_name,y=row_name,source=upper_source,size=marker_size,color="white")
        upperFig.visible = False

        # List of Lists: [Fig, and dictionary of lineplots for each sampler, tabs] ->
        # for each predefined line_y_keys
        line_plots = [self._createLinePlot(y_key, samplerCol_meta, active_x, sampling_names, active_sources, sampler_color) for y_key in line_y_keys]

        with open('exploreML/exploreML/models/active_explore_js/radio_call.js','r') as f:
            radio_call_js = f.read()

        radio_call = CustomJS(args=dict(methods=clust_methods,clust_dict=clust_dict,plot=p,
                                        up_source=upper_source, up_dict=upper_dict),code=radio_call_js)

        sample_sliders = {sampler:Slider(start=0, end=active_dim, value=0, step=1,\
                          title=title,width=360)\
                          for sampler,title in zip(sampling_names,sampling_titles)}

        radio_button_group = RadioButtonGroup(labels=[x.capitalize() for x in clust_methods], active=0)

        slider_js = {sampler:sample_sliders[sampler].js_on_change('value', self._slider_callback(sampler, active_sources, sampling_sources, symMult))\
                     for sampler in sampling_names}

        radio_button_group.js_on_click(radio_call)

        toggle = Toggle(label="Lower Triangle (Toggle)", button_type="primary")
        toggle.js_on_click(CustomJS(args=dict(plot=upperFig),code="""
            console.log('toggle: active=' + this.active, this.toString())

            plot.visible = cb_obj.active;

        """))

        #default, primary, success, warning, danger, light
        #Toggle to show and hide training examples
        train_toggle = Toggle(label="Hide Training (Toggle)", button_type="warning")
        train_toggle.js_on_click(CustomJS(args=dict(plot=trainFig),
        code="""
            console.log('toggle: active=' + this.active, this.toString())
            plot.visible = cb_obj.active;
        """))

        with open('exploreML/exploreML/models/active_explore_js/data_toggle.js','r') as f:
            data_toggle_js = f.read()

        data_toggle = Toggle(label="Show All (Toggle)", button_type="primary")
        data_toggle.js_on_click(CustomJS(args=dict(sliders=sample_sliders, active_dim=\
                                                   active_dim),
        code=data_toggle_js))

        line_selects = [self._makeLineSelect(lines[0], lines[1], y_key, i, samplerCol_meta, quant_options)\
                      for i,(y_key,lines) in enumerate(zip(line_y_keys,line_plots))]

        line_tabs = [fig[-1] for fig in line_plots]

        train_picker = ColorPicker(width=50,color='white')
        train_picker.js_link('color', trainFig.glyph, 'fill_color')

        sliders = column(list(sample_sliders.values()))

        linePlots = [column(*line) for line in list(zip(line_selects,line_tabs))]

        heatmap_layout = row(p,column(radio_button_group,toggle,sliders,data_toggle,row(train_toggle,train_picker),range_slider,select_colorbar))

        layout = self._make_layout(heatmap_layout,linePlots, plot_location)

        save(layout)

    def _make_layout(self, heatmap_layout, linePlots, plot_location):

        if (plot_location == 'below') | (plot_location == 'above'):
            line_layout = row(*linePlots)
        elif (plot_location == 'left') | (plot_location == 'right'):
            line_layout = column(*linePlots)

        if plot_location == 'right': #Right
            layout = row(heatmap_layout, line_layout)

        elif plot_location == 'left': #Left
            layout = row(line_layout, heatmap_layout)

        elif plot_location == 'above': #Above
            layout = column(line_layout, heatmap_layout)

        elif plot_location == 'below': #Above
            layout = column(heatmap_layout,line_layout)

        return layout

    def _slider_callback(self, sampler, active_sources, sampling_sources, symMult):
        callback = CustomJS(args=dict(slide_source=active_sources[sampler],
                                         active_all=sampling_sources[sampler],
                                         symMult=symMult), code=slider_callback_js)

        return callback

    def _line_callback(self, Fig, Fig2, Figs1, Figs2, samplerCol_meta):
        callback = CustomJS(args=dict(fig=Fig,
                                      fig2=Fig2,
                                      plot=Figs1,
                                      plot2=Figs2,
                                      col_meta=samplerCol_meta,
                                      yaxis=Fig.yaxis[0],
                                      yaxis2=Fig2.yaxis[0]), code=line_callback_js)

        return callback

    def _makeLineSelect(self, Fig, Figs, y_key, i, samplerCol_meta, quant_options):

        line_select = Select(title="Plot {}:".format(i+1), value=y_key,
                             options=quant_options)
        line_select.js_on_change("value", self._line_callback(Fig[0], Fig[1], Figs[0], Figs[1], samplerCol_meta))

        return line_select

    #Line figure
    def _createLinePlot(self, y_key, key_meta, active_x, sampling_names, active_sources, sampler_color):

        #Create panels for linear and log tabs
        panels = []
        figs = []
        lines = []

        for axis_type in ['log','linear']:
            Fig = figure(width=600, height=300,toolbar_location='above',
                         x_range=(0,key_meta[active_x]['max']+(key_meta[active_x]['max']*0.05)),
                         y_range=(key_meta[y_key]['min'], key_meta[y_key]['max']+(key_meta[y_key]['max']*0.05)),
                         y_axis_type=axis_type)

            Figs = {sampler:Fig.line(active_x, y_key,\
                                             source=active_sources[sampler],\
                                             color=sampler_color[sampler],\
                                             legend_label=sampler, line_width=2)\
                                             for sampler in sampling_names}
            Fig.xaxis.axis_label = active_x
            Fig.yaxis.axis_label = y_key

            Fig.legend.orientation="horizontal"
            Fig.legend.location=(0,0)
            Fig.add_layout(Fig.legend[0], 'below')
            Fig.legend.click_policy="hide"

            panel = Panel(child=Fig, title=axis_type.capitalize())
            panels.append(panel)

            figs.append(Fig)
            lines.append(Figs)

        tabs = Tabs(tabs=panels[::-1])

        return [figs, lines, tabs]


    def _makePalette(self,palette,n,ind):
        palette = np.array(all_palettes[palette][n])[ind]
        return palette

    def _makeSymAL(self, df, row_idx, col_idx, active_col, batch_col):
        """
        Makes active learning dataframe symmetrical
        """

        sym_df = pd.concat([df,df.rename({row_idx:col_idx,col_idx:row_idx},axis=1)],axis=0)\
        .sort_values([active_col,batch_col],axis=0)

        return sym_df

    def _makeClustIndex(self, df, clust_method):
        """
        # Make indices for each cluster method
        """
        if clust_method == 'None':
            row_clust_index = np.arange(df.shape[0]).tolist()
            col_clust_index = np.arange(df.shape[1]).tolist()
        else:
            try:
                row_linkages = linkage(df,method=clust_method)
                col_linkages = linkage(df.T,method=clust_method)
                row_dendrogram = dendrogram(row_linkages, no_plot=True)
                col_dendrogram = dendrogram(col_linkages, no_plot=True)
                row_clust_index = row_dendrogram['leaves']
                col_clust_index = col_dendrogram['leaves']
            except ValueError:
                print('ValueError: Invalid method given')

        #Compute the gene ranges for each cluster method
        row_range = df.index.values[row_clust_index].tolist()
        col_range = df.columns.values[col_clust_index].tolist()
        return [row_clust_index, col_clust_index, row_range, col_range]

    def _makeGImatrix(self, df, meta_vars):
        """
        Make melted GI dataframes for a given cluster index
        """

        rowName = meta_vars['rowName']
        colName = meta_vars['colName']
        valName = meta_vars['valName']

        gi_matrix = df.melt(var_name=colName, value_name=valName, ignore_index=False)\
        .rename_axis(rowName).reset_index()

        return gi_matrix

    def _addIndexCols(self, df, index, cols, meta_vars):
        """
        Respective index labels added to samples selected with (x,y) coordinates
        """
        rowName = meta_vars['rowName']
        colName = meta_vars['colName']
        rowCoord = meta_vars['rowCoord']
        colCoord = meta_vars['colCoord']

        kwargs = {rowName:index[df[rowCoord]], colName:cols[df[colCoord]]}

        data = df.assign(**kwargs)

        return data

    def _makeMaskUpper(self,df):
        mask_up = np.triu(np.ones(df.shape),1).astype(bool)
        return df.where(mask_up)
