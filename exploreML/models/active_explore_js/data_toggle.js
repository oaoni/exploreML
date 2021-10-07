console.log('toggle: active=' + this.active, this.toString())

const keys = Object.keys(sliders);
var keysLength = keys.length;

if (cb_obj.active == 1) {
    for (var i = 0; i < keysLength; i++) {
      sliders[keys[i]].value = active_dim;
    }
} else {
    for (var i = 0; i < keysLength; i++) {
      sliders[keys[i]].value = 0;
    }
}
