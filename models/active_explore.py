import numpy as np
import pandas as pd
import seaborn as sns
import math
import os
from bokeh.io import show, save
from bokeh.plotting import Figure, output_file, show, output_notebook
from bokeh.layouts import column, row
from bokeh.models import ColorBar, LinearColorMapper, BasicTicker, CustomJS, ColumnDataSource,\
 Toggle, Slider, RadioButtonGroup, Select, Legend, ColorPicker, Panel, Tabs, RangeSlider,HoverTool
from bokeh.palettes import all_palettes
from scipy.cluster.hierarchy import linkage, dendrogram
from exploreML.models.custom_tools import ResetTool

with open('exploreML/models/active_explore_js/slider_callback.js','r') as f:
    slider_callback_js = f.read()

with open('exploreML/models/active_explore_js/line_callback.js','r') as f:
    line_callback_js = f.read()

class ActiveExplore:

    """
    Args:
    data_dict: dictionary of matrix reconstruction dataframes, key value pairs
    sampling_dict: dictionary of sampling method and df, key value pairs
    is_sym: sample the points symmetrically (True or False)
    num_line_plots: number of line plots
    clust_methods: cluster methods to incorporate
    init_clust: cluster method to use initially
    active_x: column name for active iteration
    row_coord: column name of the matrix row coordinate
    col_coord: column name of the matrix col coordinate
    name: name of activeExplore module
    url: name of output file
    plot_location: location of line plots with respect to heatmap ['below','left','right','above']
    row_name: row label on heatmap
    col_name: col label on heatmap
    val_name: label for matrix entries
    """

    def __init__(self, data_dict, sampling_dict, is_sym=False, num_line_plots=2,
                 clust_methods = ['None','ward','average'], init_clust = 'None',
                 active_x='active_iter', batch_col='batch', row_coord = 'row_idx', col_coord = 'col_idx',
                 row_name='dim1', col_name='dim2', val_name='entry_value',hide_heatmap_labels=False,
                 heatmap_colors = 'default', n_colors=10, inds_colors=[1,2,4,5,6,7,8],
                 color_palette='Category10',plot_size=700, line_width=500, line_height=300,
                 name='active explorer', url='active_explorer.html', plot_location='below'):

        self.name = name
        self.numLinePlots = num_line_plots
        self.is_sym = is_sym

        # Output file
        output_file(filename=url, title=name)
        # output_notebook()

        # Load data
        M = data_dict['M']
        S_train = data_dict['S_train'].values
        sampling_names, sampling_dfs = zip(*sampling_dict.items())

        # Variables and presets
        meta_vars = dict(rowName=row_name, colName=col_name, valName=val_name,
                         rowCoord=row_coord, colCoord=col_coord) # Metadata for variables
        df_index = M.index
        df_cols = M.columns

        # Colors and palettes
        if isinstance(heatmap_colors, sns.palettes._ColorPalette):
            heatmap_colors = heatmap_colors.as_hex()
        else:
            heatmap_colors = sns.diverging_palette(260, 10, n=256).as_hex()

        # Processing inputs
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

        # Precompute the indices for the different clustering methods
        clust_dict = {method:self._makeClustIndex(M, method) for method in clust_methods}
        self.clust_dict = clust_dict

        # Active learning data
        sampling_data = {sample:self._addIndexCols(df, df_index, df_cols, meta_vars)\
                        for df,sample in zip(sampling_methods,sampling_names)}
        self.sampling_data = sampling_data

        samplerCol_meta = pd.concat([sampling_data[sampler].describe().loc[['min','max'],:]\
         for sampler in sampling_names]).describe().to_dict()

        self.samplerCol_meta = samplerCol_meta

        # Column source data of mask for each clustering method
        upper_dict = {method:self._makeGImatrix(self._makeMaskUpper(M.iloc[clust_dict[method][0],clust_dict[method][1]]),meta_vars)\
                   .dropna(axis=0).to_dict(orient='list') for method in clust_methods}

        # Collecting the quantitative columns from the sampling data
        quant_options = sampling_methods[0].describe().T.query('std > 0').index.to_list()

        line_y_keys = [col for col in quant_options[:self.numLinePlots]]

        # Make sources

        # Active learning column source data
        sampling_sources = {sampler:ColumnDataSource(data.to_dict(orient='list'))\
                        for sampler,data in sampling_data.items()}

        upper_source = ColumnDataSource(data=upper_dict[init_clust])

        # Initialize sources
        # GI column source data
        heatmap_source = ColumnDataSource(data=self._makeGImatrix(M, meta_vars).to_dict(orient='list'))
        # Active sources
        active_sources = {sampler:ColumnDataSource({key:[]\
                          for key in sampling_sources[sampler].data.keys()})\
                          for sampler in sampling_names}
        # Training data source
        train_source = ColumnDataSource(self._makeGImatrix(M.where(S_train.astype(bool)), meta_vars)\
        .dropna(axis=0)\
        .to_dict(orient='list'))

        TOOLS = "save,box_zoom,reset"
        p = Figure(title="Active Learning Explorer", frame_width=plot_size, frame_height=plot_size,
                   tools=TOOLS,
                   toolbar_location='above', x_range=clust_dict[init_clust][3],y_range=clust_dict[init_clust][2][::-1],
                   output_backend="webgl", match_aspect=True)

        p.outline_line_color = None
        p.grid.grid_line_color = None
        p.axis.axis_line_color = None
        p.axis.major_tick_line_color = None
        p.xaxis.axis_label = col_name
        p.yaxis.axis_label = row_name

        if hide_heatmap_labels:
            p.xaxis.major_label_text_font_size = '0pt'  # preferred method for removing tick labels
            p.yaxis.major_label_text_font_size = '0pt'
        else:
            p.axis.major_label_text_font_size = "7px"
            p.axis.major_label_standoff = 0
            p.xaxis.major_label_orientation = np.pi/3

        heat_max = M.values.max()
        heat_min = M.values.min()
        heat_upper_bound = min(abs(heat_min),abs(heat_max))
        heat_lower_bound = -heat_upper_bound if heat_min < 0 else heat_min

        heat_mapper = LinearColorMapper(palette=heatmap_colors, low=heat_lower_bound, high=heat_upper_bound)

        color_bar = ColorBar(color_mapper=heat_mapper, major_label_text_font_size="10px",
                             major_tick_line_color='black',
                             location=(0,0), ticker=BasicTicker(),
                             width=15,label_standoff=7)

        self.color_bar = color_bar
        p.add_layout(color_bar, "right")

        range_slider = RangeSlider(start=heat_min.round(2), end=heat_max.round(2), title="Colorbar Range",max_width=300,
                                   value=(heat_lower_bound, heat_upper_bound),step=((heat_max - heat_min)/50).round(3))
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
        self.colormap_dict = colormap_dict


        select_colorbar = Select(title="Colorbar Palette:", value="default", options=colormap_options,max_width=300)
        select_colorbar.js_on_change("value", CustomJS(args=dict(cbar=color_bar, cmap_dict=colormap_dict),code="""
            console.log('select: value=' + this.value, this.toString())

            //window.alert(cmap_dict[cb_obj.value]);
            cbar.color_mapper.palette = cmap_dict[cb_obj.value];
        """))

        # GI Heatmap
        heatFig = p.rect(x=col_name, y=row_name, height=1, width=1,
               source=heatmap_source,
               color={'field': val_name, 'transform': heat_mapper})
        self.heatmap_source = heatmap_source
        # Active
        heatFigs = {sampler:p.circle(x=col_name, y=row_name, source=active_sources[sampler], radius=0.5,\
                    color=sampler_color[sampler], line_color=sampler_color[sampler])\
                    for sampler in sampling_names}

        # Training mask
        trainFig = p.rect(x=col_name, y=row_name, source=train_source,
                          height=2, width=2, color="white")
        trainFig.visible = False

        # Upper mask
        upperFig = p.rect(x=col_name, y=row_name, source=upper_source, height=1, width=1, color="white")
        upperFig.visible = False

        p.add_tools(
            HoverTool(
                      tooltips=[('index', '@{} | @{}'.format(row_name,col_name)),(val_name, '@{}'.format(val_name))],
                      mode='mouse',
                      renderers=[trainFig, heatFig]
            )
        )

        # List of Lists: [Fig, and dictionary of lineplots for each sampler, tabs] ->
        # for each predefined line_y_keys
        line_plots = [self._createLinePlot(y_key, samplerCol_meta, active_x, sampling_names,
                      active_sources, sampler_color, line_width, line_height) for y_key in line_y_keys]
        self.line_plots = line_plots

        with open('exploreML/models/active_explore_js/radio_call.js','r') as f:
            radio_call_js = f.read()

        radio_call = CustomJS(args=dict(methods=clust_methods,clust_dict=clust_dict,plot=p,
                                        up_source=upper_source, up_dict=upper_dict),code=radio_call_js)

        sample_sliders = {sampler:Slider(start=0, end=active_dim, value=0, step=1,\
                          title=title,max_width=300)\
                          for sampler,title in zip(sampling_names,sampling_titles)}

        radio_button_group = RadioButtonGroup(labels=[x.capitalize() for x in clust_methods], active=0,max_width=300)

        slider_js = {sampler:sample_sliders[sampler].js_on_change('value', self._slider_callback(sampler, active_sources, sampling_sources, symMult))\
                     for sampler in sampling_names}

        radio_button_group.js_on_click(radio_call)

        toggle = Toggle(label="Lower Triangle (Toggle)", button_type="primary",max_width=300)
        toggle.js_on_click(CustomJS(args=dict(plot=upperFig),code="""
            console.log('toggle: active=' + this.active, this.toString())

            plot.visible = cb_obj.active;

        """))

        #default, primary, success, warning, danger, light
        #Toggle to show and hide training examples
        train_toggle = Toggle(label="Hide Training (Toggle)", button_type="warning",max_width=250)
        train_toggle.js_on_click(CustomJS(args=dict(plot=trainFig),
        code="""
            console.log('toggle: active=' + this.active, this.toString())
            plot.visible = cb_obj.active;
        """))

        with open('exploreML/models/active_explore_js/data_toggle.js','r') as f:
            data_toggle_js = f.read()

        data_toggle = Toggle(label="Show All (Toggle)", button_type="primary",max_width=300)
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

        heatmap_layout = row(column(radio_button_group,toggle,sliders,data_toggle,
                             row(train_toggle,train_picker),range_slider,select_colorbar,width=340),
                             p)

        layout = self._make_layout(heatmap_layout,linePlots, plot_location)

        # show(layout)
        # self.layout = layout
        save(layout)

    def _make_layout(self, heatmap_layout, linePlots, plot_location):

        if (plot_location == 'below') | (plot_location == 'above'):
            line_layout = row(*linePlots)
        elif (plot_location == 'left') | (plot_location == 'right'):
            line_layout = column(*linePlots)

        if plot_location == 'right': # Right
            layout = row(heatmap_layout, line_layout)

        elif plot_location == 'left': # Left
            layout = row(line_layout, heatmap_layout)

        elif plot_location == 'above': # Above
            layout = column(line_layout, heatmap_layout)

        elif plot_location == 'below': # Below
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
                                      yaxis2=Fig2.yaxis[0]), code="""
                    console.log('select: value=' + this.value, this.toString())

                    var select = cb_obj.value;
                    const keys = Object.keys(plot);
                    var keysLength = keys.length;

                    for (var i = 0; i < keysLength; i++) {
                      plot[keys[i]].glyph.y.field = select;
                      plot[keys[i]].data_source.change.emit();

                      plot2[keys[i]].glyph.y.field = select;
                      plot2[keys[i]].data_source.change.emit();
                    }

                    var mx = col_meta[select].max + col_meta[select].max * 0.05;
                    var mn = col_meta[select].min - col_meta[select].max * 0.05;

                    fig.y_range.end = mx;
                    fig.y_range.start = mn;
                    yaxis.axis_label = select;

                    fig2.y_range.end = mx;
                    fig2.y_range.start = mn;
                    yaxis2.axis_label = select;
                                      """)

        return callback

    def _makeLineSelect(self, Fig, Figs, y_key, i, samplerCol_meta, quant_options):

        line_select = Select(title="Plot {}:".format(i+1), value=y_key,
                             options=quant_options)
        line_select.js_on_change("value", self._line_callback(Fig[0], Fig[1], Figs[0], Figs[1], samplerCol_meta))

        return line_select

    #Line figure
    def _createLinePlot(self, y_key, key_meta, active_x, sampling_names, active_sources, sampler_color, line_width, line_height):

        #Create panels for linear and scatter tabs
        panels = []
        figs = []
        lines = []

        for fig_type in [{'glyph':'circle','name':'Scatter','size':0.5},{'glyph':'line','name':'Line','size':2}]:
            Fig = Figure(width=line_width, height=line_height,toolbar_location='above',
                         x_range=(0,key_meta[active_x]['max']+(key_meta[active_x]['max']*0.05)),
                         y_range=(key_meta[y_key]['min']-(key_meta[y_key]['max']*0.02),
                         key_meta[y_key]['max']+(key_meta[y_key]['max']*0.05)),
                         y_axis_type='linear',output_backend="webgl",
                         tools="save,pan,wheel_zoom")
                        #"save,pan,wheel_zoom"
            Figs = {sampler:getattr(Fig,fig_type['glyph'])(active_x, y_key,\
                                             source=active_sources[sampler],\
                                             color=sampler_color[sampler],\
                                             line_width=fig_type['size'])\
                                             for sampler in sampling_names}

            legend_factor = (50*(line_width/500))
            n_legend_rows = np.ceil(len(''.join(sampling_names))/legend_factor)

            Legends = list(Figs.items())

            if n_legend_rows > 1:
                idx = math.ceil(len(Legends)/2)
                Legends1 = Legends[:idx]
                Legends2 = Legends[idx:]

                legend1 = Legend(items=[(sampler, [glyph]) for sampler, glyph in Legends1],\
                          location=(0,0), orientation='horizontal',padding=0,margin=0)
                legend2 = Legend(items=[(sampler, [glyph]) for sampler, glyph in Legends2],\
                          location=(0,0), orientation='horizontal',padding=0,margin=0)

                Fig.add_layout(legend1, 'below')
                Fig.add_layout(legend2, 'below')
                Fig.legend.click_policy="hide"

            else:
                legend1 = Legend(items=[(sampler, [glyph]) for sampler, glyph in Legends],\
                          location=(0,0), orientation='horizontal',padding=0,margin=0)

                Fig.add_layout(legend1, 'below')
                Fig.legend.click_policy="hide"

            self.Figs = Figs

            Fig.xaxis.axis_label = active_x
            Fig.yaxis.axis_label = y_key

            panel = Panel(child=Fig, title=fig_type['name'].capitalize())
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
