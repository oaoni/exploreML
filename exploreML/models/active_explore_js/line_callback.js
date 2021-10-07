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

fig.y_range.end = col_meta[select].max;
fig.y_range.start = col_meta[select].min;
yaxis.axis_label = select;

fig2.y_range.end = col_meta[select].max;
fig2.y_range.start = col_meta[select].min;
yaxis2.axis_label = select;
