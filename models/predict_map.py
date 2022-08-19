import numpy as np
import pandas as pd
import seaborn as sns
from holoviews.plotting.util import process_cmap
from bokeh.layouts import column, row
from bokeh.models import ColorBar, LogColorMapper, LinearColorMapper, ColumnDataSource, RadioGroup, RadioButtonGroup,\
                         BasicTicker, HoverTool, Div, CustomJS
from bokeh.plotting import Figure
from itertools import count

class PredictMap:

    """
    Args:
    pred_df:
    pred_dict:
    """

    def __init__(self, pred_df, predmap_dict, toolbar=None, predmap_init_field='prediction', mapdictInit='random',
                 map_q_low=0,map_q_high=100,clust_dict=None,clust_methods=None,init_clust='None',
                 upper_source=None,upper_dict=None,constant_map=['density'],radio_button_group=None,
                 row_name='dim1',col_name='dim2',sample_sliders=None,hide_heatmap_labels=True,
                 plot_size=400,is_sym=True,toggle=None,data_toggle=None,active_dim=None):

        pred_df = self._addSym(pred_df,True,True)
        map_dict = {}
        for key1,val1 in predmap_dict.items():
            map_dict[key1] = {}
            for key2 in val1.keys():
                map_dict[key1][key2] = self._addSym(predmap_dict[key1][key2],False,False)

        predmap_labels = ["prediction", "uncertainty", "density", "similarity"]

        # Create predmap datasource
        # Assign column for entry color on prediction maps
        predmap_ds = map_dict[mapdictInit][predmap_init_field]
        pred_df_init = pred_df.assign(entry_color=predmap_ds.loc[:,'0'].values)\
                              .assign(**{k:v.loc[:,'0'].values for k,v in map_dict[mapdictInit].items()})
        pred_ds = ColumnDataSource(pred_df_init)

        # Create lists/dicts for color palettes and labels
        slider_labels_dict = dict(zip(sample_sliders.keys(),count()))
        slider_key_dict = dict(enumerate(sample_sliders.keys()))

        heatmap_colors = sns.diverging_palette(260, 10, n=256).as_hex()
        heatmap_colors2 = process_cmap('cet_CET_L17')

        pred_palette = heatmap_colors
        uncertainty_palette,density_palette,similarity_palette = [heatmap_colors2]*3
        predmap_labels_dict = dict(zip(predmap_labels,count()))
        predmap_key_dict = dict(enumerate(predmap_labels))
        predmap_palettes = [pred_palette,uncertainty_palette,density_palette,similarity_palette]
        predmap_palette_dict = dict(zip(predmap_labels,predmap_palettes))

        map_bounds = {k:[np.percentile(v.values,map_q_low),np.percentile(v.values,map_q_high)]\
                      for k,v in map_dict[mapdictInit].items()}
        map_bounds['prediction'] = [-0.3,0.3]

        map_bounds = ColumnDataSource(map_bounds)

        predmap_mapper = LinearColorMapper(palette=predmap_palette_dict[predmap_init_field],
                                           low=map_bounds.data[predmap_init_field][0],
                                           high=map_bounds.data[predmap_init_field][1])

        TOOLS = "save, box_zoom, reset"
        p3 = Figure(title='Prediction Heatmap',tools=TOOLS,
                    frame_width=plot_size, frame_height=plot_size,
                    output_backend="webgl",match_aspect =True,toolbar_location='above',
                    x_range=clust_dict[init_clust][3],y_range=clust_dict[init_clust][2][::-1])

        p3.outline_line_color = None
        p3.grid.grid_line_color = None
        p3.axis.axis_line_color = None
        p3.axis.major_tick_line_color = None
        p3.xaxis.axis_label = col_name
        p3.yaxis.axis_label = row_name

        if hide_heatmap_labels:
            p3.xaxis.major_label_text_font_size = '0pt'  # preferred method for removing tick labels
            p3.yaxis.major_label_text_font_size = '0pt'
        else:
            p3.axis.major_label_text_font_size = "7px"
            p3.axis.major_label_standoff = 0
            p3.xaxis.major_label_orientation = np.pi/3

        predmap_color_bar = ColorBar(color_mapper=predmap_mapper, major_label_text_font_size="10px",
                             major_tick_line_color='black',
                             location=(0,0), ticker=BasicTicker(),
                             width=15,label_standoff=7)

        p3.add_layout(predmap_color_bar, "right")

        heatFig = p3.rect(x=col_name, y=row_name, width=1,height=1,
                          source=pred_ds,
                          color={'field':'entry_color', 'transform': predmap_mapper})

        predmap_tooltips = [('index', '@{} | @{}'.format(row_name,col_name)),
                                ('density', '@{}'.format('density')),
                                ('similarity', '@{}'.format('similarity')),
                                ('uncertainty', '@{}'.format('uncertainty')),
                                ('prediction', '@{}'.format('prediction'))]
        p3.add_tools(
            HoverTool(
                      tooltips=predmap_tooltips,
                      mode='mouse',
                      renderers=[heatFig]
            )
        )

        # Upper mask
        upperFig2 = p3.rect(x=col_name, y=row_name, source=upper_source, height=1, width=1, color="white")
        upperFig2.visible = False

        with open('exploreML/models/active_explore_js/radio_call.js','r') as f:
            radio_call_js = f.read()

        radio_call2 = CustomJS(args=dict(methods=clust_methods,clust_dict=clust_dict,plot=p3,
                                up_source=upper_source, up_dict=upper_dict),code=radio_call_js)

        radio_button_group.js_on_click(radio_call2)

        toggle.js_on_click(CustomJS(args=dict(plot=upperFig2),code="""
            console.log('toggle: active=' + this.active, this.toString())

            plot.visible = cb_obj.active;

        """))

        def update_predmap_button(attrname, old, new):

            # Obtain sampling type and respective slider value
            curr_map_dict = slider_key_dict[radio_group_slider.active]
            slider_val = str(sample_sliders[curr_map_dict].value)

            try:
                curr_pred_map = predmap_key_dict[new]
                print(curr_map_dict,curr_pred_map)
                predmap_ds = map_dict[curr_map_dict][curr_pred_map]
            except KeyError:
                # If prediction type not in current sampling type, reset radio button
                print('exception')
                curr_pred_map = predmap_init_field
                print(curr_map_dict,curr_pred_map)
                predmap_ds = map_dict[curr_map_dict][curr_pred_map]
                radio_button_predmap.active = predmap_labels_dict[predmap_init_field]

            # Update data sources and properties
            # Update colorbar
            predmap_color_bar.color_mapper.update(low=map_bounds.data[curr_pred_map][0],
                                                  palette=predmap_palette_dict[curr_pred_map],
                                                  high=map_bounds.data[curr_pred_map][1])

            entry_values = predmap_ds.loc[:,slider_val].values if curr_pred_map not in constant_map else predmap_ds.loc[:,'0'].values
            pred_ds.data['entry_color'] = entry_values

            p2.title.text, p3.title.text = '{} Manifold'.format(str.capitalize(curr_pred_map)),\
                                           '{} Heatmap'.format(str.capitalize(curr_pred_map))

        radio_button_predmap = RadioButtonGroup(labels=list(map(str.capitalize,predmap_labels)),
                                               active=predmap_labels_dict[predmap_init_field],max_width=300)
        predmap_button_updates = radio_button_predmap.on_change('active', update_predmap_button)

        def update_slider_radio(attrname, old, new):

            # Obtain sampling type and respective slider value
            curr_map_dict = slider_key_dict[new]
            slider_val = str(sample_sliders[curr_map_dict].value)

            try:
                curr_pred_map = predmap_key_dict[radio_button_predmap.active]
                predmap_ds = map_dict[curr_map_dict][curr_pred_map]

            except KeyError:
                # If prediction type not in current sampling type, reset radio button
                curr_pred_map = predmap_init_field
                predmap_ds = map_dict[curr_map_dict][curr_pred_map]
                radio_button_predmap.active = predmap_labels_dict[predmap_init_field]

            # Update data sources and properties
            # Update pred_df cds
            entry_values = predmap_ds.loc[:,slider_val].values if curr_pred_map not in constant_map else predmap_ds.loc[:,'0'].values
            pred_ds.data = pred_df.assign(entry_color=entry_values)\
                                  .assign(**{k:v.loc[:,slider_val].values if k not in constant_map else v.loc[:,'0'].values for k,v in map_dict[curr_map_dict].items()})

            ########### Update map bounds for slider value
            map_bounds.data = {k:[np.percentile(v.loc[:,slider_val].values if k not in constant_map else v.loc[:,'0'].values,map_q_low),
            np.percentile(v.loc[:,slider_val].values if k not in constant_map else v.loc[:,'0'].values,map_q_high)]\
                          for k,v in map_dict[curr_map_dict].items()}
            map_bounds.data['prediction'] = [-0.3,0.3]

            # Update colorbar
            predmap_color_bar.color_mapper.update(low=map_bounds.data[curr_pred_map][0],
                                                  palette=predmap_palette_dict[curr_pred_map],
                                                  high=map_bounds.data[curr_pred_map][1])
           ###########

        div1 = Div(text="""
                <style>
                .spaced-radiogroup .bk:not(:last-child) {
                    margin-bottom: 1.35em !important;
                }
                </style>
        """)

        radio_group_slider = RadioGroup(labels=[""]*len(sample_sliders.keys()),
                                        active=slider_labels_dict[mapdictInit],name='slider_radio',
                                        margin=(28,5,5,5),
                                        css_classes=["spaced-radiogroup"],
                                        width=15)

        radio_slider_updates = radio_group_slider.on_change('active', update_slider_radio)

        def update_predmap_slider(attrname, old, new):

            curr_map_dict = slider_key_dict[radio_group_slider.active]
            curr_pred_map = predmap_key_dict[radio_button_predmap.active]
            slider_val = str(sample_sliders[curr_map_dict].value)

            predmap_ds = map_dict[curr_map_dict][curr_pred_map]

            entry_values = predmap_ds.loc[:,slider_val].values if curr_pred_map not in constant_map else predmap_ds.loc[:,'0'].values
            pred_ds.data = pred_df.assign(entry_color=entry_values)\
                                  .assign(**{k:v.loc[:,slider_val].values if k not in constant_map else v.loc[:,'0'].values for k,v in map_dict[curr_map_dict].items()})

            ########### Update map bounds for slider value
            map_bounds.data = {k:[np.percentile(v.loc[:,slider_val].values if k not in constant_map else v.loc[:,'0'].values,map_q_low),
            np.percentile(v.loc[:,slider_val].values if k not in constant_map else v.loc[:,'0'].values,map_q_high)]\
                          for k,v in map_dict[curr_map_dict].items()}
            map_bounds.data['prediction'] = [-0.3,0.3]

            # Update colorbar
            predmap_color_bar.color_mapper.update(low=map_bounds.data[curr_pred_map][0],
                                                  palette=predmap_palette_dict[curr_pred_map],
                                                  high=map_bounds.data[curr_pred_map][1])
           ###########

        slider_updates = {sampler:sample_sliders[sampler].on_change('value_throttled', update_predmap_slider)\
                     for sampler in sample_sliders.keys()}

        def toggle_predmap_slider(event):

            if event:
                update_predmap_slider('value_throttled',0,active_dim)
            else:
                update_predmap_slider('value_throttled',active_dim,0)

        data_toggle.on_click(toggle_predmap_slider)

        # with open('exploreML/models/active_explore_js/data_toggle.js','r') as f:
        #     data_toggle_js = f.read()
        #
        # data_toggle.js_on_click(CustomJS(args=dict(sliders=sample_sliders, active_dim=\
        #                                            1000),
        # code=data_toggle_js))

        #### Manifold plot
        TOOLS = "save, pan, box_zoom, wheel_zoom, reset"
        p2 = Figure(title='Prediction Manifold',tools=TOOLS,toolbar_location='above',
                    frame_width=plot_size, frame_height=plot_size, output_backend="webgl")
        p2.xaxis.axis_label = "umap 1"
        p2.yaxis.axis_label = "umap 2"

        manifoldFig = p2.scatter(x='x',y='y',source=pred_ds,size=1,
                                 color={'field':'entry_color', 'transform': predmap_mapper})

        p2.add_tools(
            HoverTool(
                      tooltips=predmap_tooltips,
                      mode='mouse',
                      renderers=[manifoldFig]
            )
        )

        toolbar.children.append(radio_button_predmap)
        toolbar.children[2] = row(radio_group_slider,toolbar.children[2])
        for child in toolbar.select_one({'name':'slider_col'}).children:
            child.width = 275
        layout = column(p3,p2,div1)

        self.layout = layout

    def _addSym(self, df, change_col=True, ignore_index=True):

        if change_col:
            symDF = pd.concat([df,df.assign(gene1=df['gene2'],
                  gene2=df['gene1'],
                  row_coord=df['col_coord'],
                  col_coord=df['row_coord'])],axis=0,ignore_index=ignore_index)
        else:
            symDF = pd.concat([df,df],ignore_index=ignore_index)

        return symDF
