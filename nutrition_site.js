var _____WB$wombat$assign$function_____=function(name){return (self._wb_wombat && self._wb_wombat.local_init && self._wb_wombat.local_init(name))||self[name];};if(!self.__WB_pmw){self.__WB_pmw=function(obj){this.__WB_source=obj;return this;}}{
let window = _____WB$wombat$assign$function_____("window");
let self = _____WB$wombat$assign$function_____("self");
let document = _____WB$wombat$assign$function_____("document");
let location = _____WB$wombat$assign$function_____("location");
let top = _____WB$wombat$assign$function_____("top");
let parent = _____WB$wombat$assign$function_____("parent");
let frames = _____WB$wombat$assign$function_____("frames");
let opens = _____WB$wombat$assign$function_____("opens");


function get_query() {
    var url = document.location.href;
    var qs = url.substring(url.indexOf('?') + 1).split('&');
    for (var i = 0, result = {}; i < qs.length; i++) {
        qs[i] = qs[i].split('=');
        if (qs[i][1] != undefined)
            qs[i][1] = qs[i][1].replace('+', ' ');
        result[qs[i][0]] = decodeURIComponent(qs[i][1]);
    }
    return result;
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

function updateMenu() {
    window.location.href = "?locationNum=" + $('#location-select-menu').val() + "&dtdate=" + $('#date-select-menu').val();
}

function getDate(offset) {
    var today = new Date();
    var toReturn = new Date();
    toReturn.setDate(today.getDate() + offset);
    var dd = String(toReturn.getDate());
    var mm = String(toReturn.getMonth() + 1); //January is 0!
    var yyyy = today.getFullYear();
    return mm + '/' + dd + '/' + yyyy;
}

function fillDates(element) {
    //  7 days from today
    for ($i = 0; $i < 7; $i = $i + 1) {
        text = getDate($i);
        $(element).append(new Option(text, text));
    }
}

function fillMenuType(DTDATE) {
    var elem = $('#meal-type-select-menu');
    if (elem.length != 0) {
        let d = new Date(DTDATE);
        let day = d.getDay();
        // if sat or sunday
        if (day == 0 || day == 6) {
            $(elem).append(new Option("Brunch", "Lunch"));
            $(elem).append(new Option("Dinner", "Dinner"));
        }
        else {
            $(elem).append(new Option("Breakfast", "Breakfast"));
            $(elem).append(new Option("Lunch", "Lunch"));
            $(elem).append(new Option("Dinner", "Dinner"));
        }
    }
}

function updateImHaving() {
    let selectedDate = $('#date-select-meal').val();
    let d = new Date(selectedDate);
    let day = d.getDay();
    // to check if it has b,l,d or just b,d.
    let curSelected = $('#meal-type-select-menu')[0].length;
    // only update if change is required (if selected date => b,d and current => b,l,d === change)
    if (((day == 0 || day == 6) && curSelected == 3) || ((day != 0 && day != 6) && curSelected == 2)) {
        $('#meal-type-select-menu').empty()
        fillMenuType(d)
    }
}

$(document).ready(function () {


    // fill both select elements
    fillDates($('#date-select-search'));
    fillDates($('#date-select-menu'));

    // ---------- Handling GET Params on location.aspx ---------- 

    // set LOCATION_NUM and DTDATE based on get or default
    get_query().locationNum != undefined ? LOCATION_NUM = get_query().locationNum : LOCATION_NUM = "16"
    get_query().dtdate != undefined ? DTDATE = get_query().dtdate : DTDATE = getDate(0);

    // set default val for date-select-menu
    $('#date-select-menu').val(getDate(0));

    // set longmenu href for selected / today's date and selected / south campus dining hall
    $('#longmenu-link').attr('href', "longmenu.aspx?locationNum=" + LOCATION_NUM + "&dtdate=" + DTDATE + "&mealName=Breakfast");

    // set "AT" if locationNum is passed
    $('#location-select-menu').val(LOCATION_NUM);

    // set "ON" if dtdate is passed
    $('#date-select-menu').val(DTDATE)

    // ---------- Handling GET Params on search.aspx ---------- 

    // set SEARCH_LOCATION_NUM and SEARCH_DTDATE based on get or default
    get_query().strCurSearchLocs != undefined ? SEARCH_LOCATION_NUM = get_query().strCurSearchLocs : SEARCH_LOCATION_NUM = "ALL"
    get_query().strCurSearchDays != undefined ? SEARCH_DTDATE = get_query().strCurSearchDays : SEARCH_DTDATE = "ALL";

    // set "AT" if strCurSearchLocs is passed
    $('#location-select-search').val(SEARCH_LOCATION_NUM)

    // set "ON" if strCurSearchDays is passed
    $('#date-select-search').val(SEARCH_DTDATE)



    // ---------- Handling GET Params on longmenu.aspx ---------- 
    get_query().mealName != undefined ? MEALNAME = get_query().mealName : MEALNAME = "Breakfast";
    fillMenuType(DTDATE);

    fillDates($('#date-select-meal'))

    // set "I'm Having" if mealName is passed
    $('#meal-type-select-menu').val(MEALNAME);

    // set "AT" if strCurSearchLocs is passed
    $('#location-select-meal').val(LOCATION_NUM)

    // set "ON" if strCurSearchDays is passed
    $('#date-select-meal').val(DTDATE)

    $('#date-select-meal').on('change', updateImHaving);





    $(".section-ut_tabs .nav-tabs .nav-item a").click(function (e) {
        e.preventDefault();
        // hide current pane
        $(this).closest('.section-ut_tabs').find('.tab-pane.fade.active.show').removeClass("active show");
        $active = $(this).closest('ul.nav').find('a.active');
        $active.removeClass("active");
        $active.attr('aria-selected', 'false');

        // show other pane
        $('#' + $(this).attr('aria-controls')).addClass("active show");
        $(this).addClass("active");
        $(this).attr('aria-selected', 'true');
    });

    $('#location-select-menu').on('change', updateMenu);

    $('#date-select-menu').on('change', updateMenu);

    $('#btn-set-filter').click(function (e) {
        e.preventDefault();

        window.open("allergenfilter.aspx?strcurlocationnum=" + LOCATION_NUM, "asdfasdfasd", 'width=600, height=620');
        return;
    });

    // Display selected allergen and legend filters.
    var reference_array_legend = ["Dairy", "Eggs", "Fish", "Gluten", "Nuts", "Soy", "Shellfish", "Sesame", "Vegetarian", "Vegan", "Locally Grown", "Smart Choice", "Halal Friendly"];
    var reference_array_allergens = ["Milk", "Eggs", "Fish", "Crustacean Shellfish", "Tree Nuts", "Peanuts", "Wheat", "Soybeans", "Sesame", "Halal"];

    var legend_filters_array = getCookie("SavedWebCodes").split(']');
    var allergen_filters_array = getCookie("SavedAllergens").split(']');

    var selected_legend = [];
    var selected_allergens = [];

    let len_legend = legend_filters_array.length;
    let len_allergen = allergen_filters_array.length;

    for (let i = 0; i < len_legend - 1; i++) {
        if (legend_filters_array[i][0] != '[') {
            selected_legend.push(reference_array_legend[i]);
        }
    }

    for (let i = 0; i < len_allergen - 1; i++) {
        if (allergen_filters_array[i][0] != '[') {
            selected_allergens.push(reference_array_allergens[i]);
        }
    }

    if (selected_legend.length != 0) {
        $('#legend-filt-text').removeClass('d-none');
        let text = "";
        legend_filters_array[len_legend - 1][0] == "C" ? text += "Contains: " : text += "Doesn't Contain: "
        text += selected_legend.join(', ');
        $('#legend-filter-disp').html(text);
    }

    if (selected_allergens.length != 0) {
        $('#legend-br').removeClass('d-none');
        $('#allergen-filt-text').removeClass('d-none');
        text = "";
        allergen_filters_array[len_allergen - 1][0] == "C" ? text += "Contains: " : text += "Doesn't Contain: "
        text += selected_allergens.join(', ');
        $('#allergen-filter-disp').html(text);
    }

    $('#site-header-nav-toggle').click(function (e) {
        // if hidden -> show navbar.
        var elem = $('.site-header__nav')[0];
        if ($(elem).attr('aria-hidden') == 'true') {
            // $(elem).css('display','block');
            $(elem).attr('aria-hidden', false);
            $('#site-header-nav-toggle').attr('aria-expanded', true);	// let the button know that navbar is shown
        }
        // else make it go whoossh...
        else {
            $(elem).attr('aria-hidden', true);
            $('#site-header-nav-toggle').attr('aria-expanded', false);
            // $(elem).css('display','none');
        }
    });

});
}

/*
     FILE ARCHIVED ON 00:37:24 Mar 02, 2026 AND RETRIEVED FROM THE
     INTERNET ARCHIVE ON 23:47:08 May 11, 2026.
     JAVASCRIPT APPENDED BY WAYBACK MACHINE, COPYRIGHT INTERNET ARCHIVE.

     ALL OTHER CONTENT MAY ALSO BE PROTECTED BY COPYRIGHT (17 U.S.C.
     SECTION 108(a)(3)).
*/
/*
playback timings (ms):
  capture_cache.get: 0.458
  load_resource: 106.005
  PetaboxLoader3.resolve: 76.238
  PetaboxLoader3.datanode: 12.489
*/
