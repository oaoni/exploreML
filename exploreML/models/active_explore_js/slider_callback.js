var slideVal = cb_obj.value;
var data = slide_source.data;
const keys = Object.keys(data);
var keysLength = keys.length;

var active_map = new Map();
var all_map = new Map();

for (var i = 0; i < keysLength; i++) {

  // Assign each key in the slide source to a map variable
  active_map.set(keys[i], data[keys[i]]);

  // Set all data to the current slice
  all_map.set(keys[i], active_all.data[keys[i]].slice(0,slideVal*symMult));

  // Clear active map array
  active_map.get(keys[i]).splice(0, active_map.get(keys[i]).length);

  // Assign new data to active map
  active_map.set(keys[i], active_map.get(keys[i]).push(...all_map.get(keys[i])));
}

slide_source.change.emit();
