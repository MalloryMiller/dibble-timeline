let YEAR_RANGE = [2000, 2025];
let YEAR_STEPS = 1



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

}



function update() {

    document.getElementById("year-t").value = document.getElementById("year-s").value

    update_from_text()

}

function update_from_text() {
    document.getElementById("year-s").value = document.getElementById("year-t").value

    var year = document.getElementById("year-t").value
    document.getElementById("velocity").src = 'images/velocities/' + year + '_v.png'
    document.getElementById("elevation").src = 'images/elevation/' + year + '_e.png'

}