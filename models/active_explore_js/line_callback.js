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
