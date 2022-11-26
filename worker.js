import { parse } from 'https://cdn.jsdelivr.net/npm/@vanillaes/csv@3.0.1/index.min.js'

const start = Date.now();
fetch('/voter_cards.smol.csv')
  .then((response) => response.text())
  .then((csv) => {
    console.log('got csv in', Date.now() - start);
    const s2 = Date.now();
    const parsed = parse(csv);
    console.log('parsed in', Date.now() - s2);
    const s3 = Date.now();
    postMessage(parsed);
    console.log('sent in', Date.now() - s3);
  });
