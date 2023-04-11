import { createApp } from 'vue'

mapboxgl.accessToken = 'pk.eyJ1IjoiZGltdmEiLCJhIjoiY2plYzhtMTM5MG5yazJ4bGE0OHZrcHpnZCJ9.u9hqKMLwpq-JHGyhAW2GeQ';
var map = new mapboxgl.Map({
    container: 'map', // container id
    style: 'mapbox://styles/mapbox/light-v11',
});

// Hide loading bar once tiles from geojson are loaded
map.on('data', function(e) {
    if (e.dataType === 'source' && e.sourceId === 'zones-layer') {
        document.getElementById("loader").style.display = "none";
    }
});

// disable map rotation using right click + drag
map.dragRotate.disable();

// disable map rotation using touch rotation gesture
map.touchZoomRotate.disableRotation();

// add zoom controls to the map
map.addControl(new mapboxgl.NavigationControl({showCompass: false}));

// add geolocation control to the map
map.addControl(new mapboxgl.GeolocateControl({
    positionOptions: {
        enableHighAccuracy: true
    },
    trackUserLocation: true
}));

map.setZoom(11.75);
map.setCenter([-122.42936665634733, 37.75967613988033]);


map.on('load', function () {
  map.addSource('precincts', {
    type: 'geojson',
    data: {
      "type": "FeatureCollection",
      "features": []
    }
  });

  map.addLayer({
      'id': 'precincts-layer',
      'type': 'fill',
      'source': 'precincts',
      'paint': {
          'fill-opacity': 0.7,
          'fill-color': ['get', 'fill'],
          'fill-outline-color': '#000',
      }
  });
});

const PCT = "precinct";

function computePossibilities(data, columns) {
  let arr = [];
  for(let i = 0; i < data[0].length; ++i) {
    arr.push(new Set());
  }
  for (let row of data) {
    for(let i = 0; i < row.length; ++i) {
      arr[i].add(row[i]);
    }
  }

  let ret = {}
  for(let i = 0; i < columns.length; ++i) {
    let list = Array.from(arr[i]);
    list.sort();
    ret[columns[i]] = list;
  }

  return ret;
}

var geojson;
var geojson_index = {}; // precinct -> obj
var precinct_vote_totals;

function selectedPageIndex(filters, pageIndex) {
  let index;
  for (const [key, value] of Object.entries(filters)) {
    if (value) {
      if (index !== undefined && index != pageIndex[key]) {
        console.log("something weird has happened, we've moved from page " + pageIndex[key] + " to " + index);
        index = undefined;
        break;
      }

      index = pageIndex[key];
    }
  }
  return index;
}

createApp({
  mounted() {
    console.log('mounted');

    const start = Date.now();
    const myWorker = new Worker('worker.js', { type: "module" });
    myWorker.onmessage = (e) => {
      console.log('Message received from worker in a total of', Date.now() - start);
      let i = e.data.index;
      this.data[i] = e.data.data;
      this.columns[i] = this.data[i].shift();

      const poss = computePossibilities(this.data[i], this.columns[i]);
      for (const [key, value] of Object.entries(poss)) {
        this.possibilities[key] = value;
      }
      for(const col of this.columns[i]) {
        if(col !== PCT) {
          this.pageIndex[col] = i;
        }
      }
    };

    fetch('/precincts.geojson')
      .then((response) => response.json())
      .then((data) => {
        console.log('geojson', data);
        geojson = data;
        for (let o of geojson.features) {
          const pct = o.properties.Prec_2022;
          geojson_index[pct] = o;
        }
        console.log(geojson);
        console.log(geojson_index);
      });

    fetch('/precinct_vote_totals.json')
      .then((response) => response.json())
      .then((data) => {
        precinct_vote_totals = data;
        console.log(precinct_vote_totals);
      });

  },
  data() {
    return {
      filters: {},

      data: [],  // per ballot page
      columns: [],  // per ballot page

      possibilities: {},  // possibilities for every race
      pageIndex: [], // race -> ballot page index
    }
  },
  computed: {
    allRaces() {
      const index = selectedPageIndex(this.filters, this.pageIndex);

      let ret = [];
      for(const [i, cdata] of this.columns.entries()) {
        if (index !== undefined && index != i) {
          continue;
        }

        if(cdata) {
          for(const col of cdata) {
            if(col !== PCT) {
              ret.push(col);
            }
          }
        }
      }
      return ret;
    },
  },
  watch: {
    filters: {
      handler(val) {
        const precincts = precinctVotes(this.data, this.columns, this.filters, this.pageIndex, this.possibilities.precinct);

        let percents = [];
        for(const [pct, votes] of Object.entries(precincts)) {
          const percent = votes / precinct_vote_totals[pct];
          percents.push(percent);
          console.log(pct, percent);
        }

        const mean = computeMean(percents);
        const stddev = computeStddev(percents);
        for (let k in geojson_index) {
          if (precinct_vote_totals[k]) {
            const percent = precincts[k] / precinct_vote_totals[k];
            geojson_index[k].properties.fill = color(percent, mean, stddev);
          } else {
            console.log("no precinct found:", k);
            geojson_index[k].properties.fill = "#cccccc";
          }
        }

        const pcts = map.getSource('precincts');
        if (pcts) {
          pcts.setData(geojson);
          console.log('pcts', geojson);
        }
      },
      deep: true,
    },
  },
}).mount('#app');

function precinctVotes(data, columns, filters, pageIndex, allPrecincts) {
  const index = selectedPageIndex(filters, pageIndex);
  if (index === undefined) {
    return {};  // TODO: return something better?
  }
  return precinctVotesImpl(data[index], columns[index], filters, allPrecincts);
}

function color(percent, mean, stddev) {
  const dist = Math.abs(percent - mean) / stddev;
  const colorDist = Math.min(100 * dist, 255);
  let hex = Math.round(255 - colorDist).toString(16);
  if(hex.length < 2) {
    hex = "0" + hex;
  }

  if (percent < mean) {
    return "#" + hex + hex + "ff";
  } else {
    return "#ff" + hex + hex;
  }
}

function precinctVotesImpl(data, columns, filters, allPrecincts) {
  let queryArr = [];
  for(const [i, col] of columns.entries()) {
    if (filters[col]) {
      queryArr.push([i, filters[col]]);
    }
  }

  let precincts = {};
  for(const pct of allPrecincts) {
    precincts[pct] = 0;
  }
  for(const row of data) {
    let add = true;
    for(const [i, col] of queryArr) {
      if(row[i] !== col) {
        add = false;
        break;
      }
    }
    if(add) {
      precincts[row[0]]++;
    }
  }

  console.log(precincts);
  return precincts;
}

function computeMean(arr) {
  let sum = 0;
  for (let i = 0; i < arr.length; i++) {
    sum += arr[i];
  }
  return sum / arr.length;
}

function computeStddev(arr) {
  let avg = computeMean(arr);
  let sum = 0;
  for (let i = 0; i < arr.length; i++) {
    sum += Math.pow(arr[i] - avg, 2);
  }
  let variance = sum / arr.length;
  return Math.sqrt(variance);
}
