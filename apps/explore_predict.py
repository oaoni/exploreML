from exploreML.models import ActiveExplore
from exploreML.models import PredictMap
from bokeh.layouts import column, row

class ExploreML:


    def __init__(self,grid_shape=(1,1),**kwargs):

        self.grid_shape = grid_shape
        self.layouts = []
        #maybe map_p_high/low


    def addActiveExplore(self,data_dict,sampling_dict,**kwargs):

        active = ActiveExplore(data_dict, sampling_dict, **kwargs)

        self.layouts += [active.layout]
        self.toolbar = active.toolbar
        self.clust_dict = active.clust_dict # Index clusters for heatmap
        self.clust_methods = active.clust_methods
        self.upper_source = active.upper_source
        self.upper_dict = active.upper_dict
        self.row_name = active.row_name
        self.col_name = active.col_name
        self.sample_sliders = active.sample_sliders
        self.plot_size = active.plot_size
        self.radio_button_group = active.radio_button_group
        self.toggle = active.toggle
        self.data_toggle = active.data_toggle
        self.active_dim = active.active_dim


    def addPredictMap(self,pred_df,map_dict,**kwargs):

        predict = PredictMap(pred_df, map_dict, toolbar=self.toolbar,
                             clust_dict=self.clust_dict,clust_methods=self.clust_methods,
                             upper_source=self.upper_source,upper_dict=self.upper_dict,
                             row_name=self.row_name,col_name=self.col_name,
                             radio_button_group=self.radio_button_group,toggle=self.toggle,
                             sample_sliders=self.sample_sliders,plot_size=self.plot_size,
                             data_toggle=self.data_toggle,active_dim=self.active_dim,**kwargs)
        self.layouts += [predict.layout]

    def Layout(self):
        self.layout = row(*self.layouts)
