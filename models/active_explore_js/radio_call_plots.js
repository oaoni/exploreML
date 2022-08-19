console.log('radio_button_group: active=' + this.active, this.toString())

//Store radioVal for clustering methods
let radioVal = cb_obj.active;

let method = methods[radioVal];
let x_range = clust_dict[method][3];
let y_range = [].concat(clust_dict[method][2]).reverse();

plot1.x_range.factors = x_range;
plot1.y_range.factors = y_range;

plot2.x_range.factors = x_range;
plot2.y_range.factors = y_range;

let cdsLists = up_dict[method];

//Reorder mask
//Assign mask source to variable
var data = up_source.data;
var keys = Object.keys(data);
var keysLength = keys.length;

// Reorder mask
var mask_map = new Map();
var new_map = new Map();
for (var i = 0; i < keysLength; i++) {

  //Assign mask source to map variable
  mask_map.set(keys[i], data[keys[i]]);

  // Reassign CDS
  new_map.set(keys[i], cdsLists[keys[i]]);

  // Clear old mask CDS
  mask_map.get(keys[i]).splice(0, mask_map.get(keys[i]).length);

  // Add new mask cds
  mask_map.set(keys[i], mask_map.get(keys[i]).push(...new_map.get(keys[i])));

}

up_source.change.emit();
