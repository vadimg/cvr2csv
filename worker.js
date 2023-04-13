import { parse } from 'https://cdn.jsdelivr.net/npm/@vanillaes/csv@3.0.1/index.min.js'

const start = Date.now();
for(let i = 0; i < 5; ++i) {
  fetch('/data/voter_cards.' + (i+1) + '.csv')
    .then((response) => response.text())
    .then((csv) => {
      console.log('got csv in', Date.now() - start);
      const s2 = Date.now();
      const parsed = parse(csv);
      console.log('parsed in', Date.now() - s2);
      const s3 = Date.now();
      postMessage({index: i, data: parsed});
      console.log('sent in', Date.now() - s3);
    });
}
