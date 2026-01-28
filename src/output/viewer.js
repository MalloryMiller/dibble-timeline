let YEAR_RANGE = [2000, 2025];
let YEAR_STEPS = 1

function exists(src, indicator) {
    var img = new Image();
    img.onerror = function() {document.getElementById(indicator).classList.add('missing')};
    img.src = src;
}

function file_indicator_setup(ftype) {
    let yearbar = document.getElementById(ftype + "-files");

    cur = YEAR_RANGE[0]
    var total_years = YEAR_RANGE[1] - YEAR_RANGE[0] / YEAR_STEPS
    while (cur <= YEAR_RANGE[1]) {

        var box = document.createElement('div')
        box.id = cur + "_" + ftype[0]
        box.style = "width: " + 100 / total_years + "%;"
        exists('images/' + ftype + '/' + cur + '_' + ftype[0] +".png", box.id);
        
        yearbar.appendChild(box)

        cur += YEAR_STEPS
    }

}


function set_ranges() {

    let yearbar = document.getElementById("year-s");
    let yeartyp = document.getElementById("year-t");

    yearbar.max = YEAR_RANGE[1]
    yearbar.min = YEAR_RANGE[0]
    yearbar.value = YEAR_RANGE[0]
    yearbar.step = YEAR_STEPS

    yeartyp.max = YEAR_RANGE[1]
    yeartyp.min = YEAR_RANGE[0]
    yeartyp.value = YEAR_RANGE[0]
    yeartyp.step = YEAR_STEPS

    update()

    file_indicator_setup('velocities')
    file_indicator_setup('elevation')
    file_indicator_setup('rema')

}




function update() {

    document.getElementById("year-t").value = document.getElementById("year-s").value

    update_from_text()

}

function get_cur_selection(year, dataset) {
    return 'images/' + dataset + "/" + year + "_" + dataset[0] + '.png'
}

function update_from_text() {
    document.getElementById("year-s").value = document.getElementById("year-t").value
    var year = document.getElementById("year-t").value


    console.log(get_cur_selection(year, document.getElementById('dataset-selector').value))
    document.getElementById("image").src = get_cur_selection(year, document.getElementById('dataset-selector').value)
    //document.getElementById("velocity").src = 'images/velocities/' + year + '_v.png'
    //document.getElementById("elevation").src = 'images/elevation/' + year + '_e.png'
    //document.getElementById("rema").src = 'images/rema/' + year + '_r.png'

}