import os
import glob
import json
from dataclasses import dataclass
from typing import Optional
import pickle

DIR = "/Users/vadim/Downloads/CVR_Export_20221012160533"
DIR = "/Users/vadim/Downloads/CVR_Export_20221108200035"
DIR = "/Users/vadim/Downloads/CVR_Export_20221108235925"

@dataclass
class Measure:
    id: Optional[int] = None
    yes_id: Optional[int] = None
    no_id: Optional[int] = None

@dataclass
class Voter:
    """Class for keeping track of each voter."""
    measure_d: Optional[bool] = None
    measure_e: Optional[bool] = None

def get_voters():
    measure_d = Measure()
    measure_e = Measure()

    with open(os.path.join(DIR, "ContestManifest.json")) as f:
        obj = json.load(f)

    for l in obj["List"]:
        if l["Description"] == "Measure D":
            measure_d.id = l["Id"]
        elif l["Description"] == "Measure E":
            measure_e.id = l["Id"]

    assert measure_d.id
    assert measure_e.id
    assert measure_d.id != measure_e.id

    with open(os.path.join(DIR, "CandidateManifest.json")) as f:
        obj = json.load(f)

    for l in obj["List"]:
        for m in (measure_d, measure_e):
            if l["ContestId"] == m.id:
                if l["Description"] == "Yes":
                    m.yes_id = l["Id"]
                elif l["Description"] == "No":
                    m.no_id = l["Id"]

    for m in (measure_d, measure_e):
        assert m.yes_id
        assert m.no_id
        assert m.yes_id != m.no_id
    print(measure_d, measure_e)



    paths = glob.glob(os.path.join(DIR, "CvrExport*.json"))
    voters = []
    for p in paths:
        with open(p) as f:
            obj = json.load(f)

        for s in obj["Sessions"]:
            voter = Voter()

            cvrs = [s["Original"], s.get("Modified", {})]
            cvrs = [x for x in cvrs if x.get("IsCurrent")]
            cards = [card for x in cvrs for card in x["Cards"]]

            for card in cards:
                for contest in card["Contests"]:
                    for m in (measure_d, measure_e):
                        if contest["Id"] == m.id:
                            for mark in contest["Marks"]:
                                if mark["IsVote"]:
                                    if mark["CandidateId"] == m.yes_id:
                                        if m == measure_d:
                                            assert voter.measure_d is None
                                            voter.measure_d = True
                                        else:
                                            assert voter.measure_e is None
                                            voter.measure_e = True
                                    if mark["CandidateId"] == m.no_id:
                                        if m == measure_d:
                                            assert voter.measure_d is None
                                            voter.measure_d = False
                                        else:
                                            assert voter.measure_e is None
                                            voter.measure_e = False
            voters.append(voter)

    return voters

def save_voters():
    voters = get_voters()
    with open("voters.pkl", "wb") as f:
        pickle.dump(voters, f)

def load_voters():
    with open("voters.pkl", "rb") as f:
        return pickle.load(f)

voters = load_voters()

votes = [0, 0]
de = 0
d = 0
e = 0
d_noe = 0
e_nod = 0
nod_noe = 0
for v in voters:
    if v.measure_d and v.measure_e:
        de += 1
    elif v.measure_d and v.measure_e is None:
        d += 1
    elif v.measure_d and v.measure_e == False:
        d_noe += 1
    elif v.measure_e and v.measure_d is None:
        e += 1
    elif v.measure_e and v.measure_d == False:
        e_nod += 1
    elif v.measure_d == False and v.measure_e == False:
        nod_noe += 1


    if v.measure_d is not None:
        if v.measure_d:
            votes[1] += 1
        else:
            votes[0] += 1

print(votes)
print(de, d, e, d_noe, e_nod, nod_noe)
