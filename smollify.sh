#!/bin/bash

# Creates smol voter_cards files, for faster testing. Need to update worker.js to read them instead.

for i in {1..5}
do
    head -10000 "data/voter_cards.$i.csv" > "data/voter_cards.$i.smol.csv"
done
