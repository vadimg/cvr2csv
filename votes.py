import os
import glob
import json
from dataclasses import dataclass, field
from typing import Optional
import pickle
import string
import csv

DIR = "/Users/vadim/Downloads/CVR_Export_20221012160533"
DIR = "/Users/vadim/Downloads/CVR_Export_20221108200035"
DIR = "/Users/vadim/Downloads/CVR_Export_20221108235925"


@dataclass(kw_only=True)
class ContestSimple:
    id: int
    name: str
    choices: dict[int, str] = field(default_factory=dict)

    def serialize(self, votes):
        assert len(votes) <= 1
        vote = votes[0] if len(votes) > 0 else None
        return {self.name: vote}

@dataclass
class ContestMultiple(ContestSimple):
    num_choices: int

    def serialize(self, votes):
        ret = {}
        for i in range(self.num_choices):
            vote = votes[i] if i < len(votes) else None
            ret[f"{self.name}: CHOICE {string.ascii_uppercase[i]}"] = vote
        return ret

@dataclass
class ContestRanked(ContestSimple):
    num_ranks: int

    def serialize(self, votes):
        ret = {}
        for i in range(self.num_ranks):
            vote = votes[i] if i < len(votes) else None
            ret[f"{self.name}: RANK {i + 1}"] = vote
        return ret

@dataclass(kw_only=True)
class Vote:
    contest: ContestSimple | ContestMultiple | ContestRanked
    choices: list[str] = field(default_factory=list)

    def serialize(self):
        return self.contest.serialize(self.choices)

@dataclass
class Voter:
    precinct: str
    votes: list[Vote] = field(default_factory=list)

    def serialize(self):
        ret = {"precinct": self.precinct}
        for vote in self.votes:
            ret.update(vote.serialize())
        return ret

# TODO
ballot_defs = {}  # id -> def

def get_voters():
    precinct_defs = {}  # id -> str

    with open(os.path.join(DIR, "PrecinctManifest.json")) as f:
        obj = json.load(f)

    for l in obj["List"]:
        precinct_defs[l["Id"]] = l["Description"]

    with open(os.path.join(DIR, "ContestManifest.json")) as f:
        obj = json.load(f)

    for l in obj["List"]:
        vote_def = None
        if l["VoteFor"] == 1 and l["NumOfRanks"] <= 1:
            vote_def = ContestSimple(id=l["Id"], name=l["Description"])
        elif l["VoteFor"] == 1 and l["NumOfRanks"] > 1:
            vote_def = ContestRanked(id=l["Id"], name=l["Description"], num_ranks=l["NumOfRanks"])
        elif l["VoteFor"] > 1:
            assert l["NumOfRanks"] == 0
            vote_def = ContestMultiple(id=l["Id"], name=l["Description"], num_choices=l["VoteFor"])
        else:
            assert False, "Unknown"

        ballot_defs[vote_def.id] = vote_def

    with open(os.path.join(DIR, "CandidateManifest.json")) as f:
        obj = json.load(f)

    for l in obj["List"]:
        contest_id = l["ContestId"]
        ballot_defs[contest_id].choices[l["Id"]] = l["Description"]


    paths = glob.glob(os.path.join(DIR, "CvrExport*.json"))
    voters = []
    for p in paths:
        with open(p) as f:
            obj = json.load(f)

        for s in obj["Sessions"]:

            cvrs = [s["Original"], s.get("Modified", {})]
            cvrs = [x for x in cvrs if x.get("IsCurrent")]

            for cvr in cvrs:
                precinct_id = cvr["PrecinctPortionId"]
                for card in cvr["Cards"]:
                    voter = Voter(precinct=precinct_defs[precinct_id])
                    voters.append(voter)
                    for contest in card["Contests"]:
                        vote = Vote(contest=ballot_defs[contest["Id"]])
                        voter.votes.append(vote)

                        contest["Marks"].sort(key=lambda x: x["Rank"])
                        for mark in contest["Marks"]:
                            if mark["IsVote"]:
                               vote.choices.append(vote.contest.choices[mark["CandidateId"]])

    return voters

def get_fieldnames():
    ret = ['precinct']
    for b in ballot_defs.values():
        ret.extend(b.serialize([]).keys())
    return ret

voters = get_voters()

print(get_fieldnames())

with open("voters.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=get_fieldnames())
    writer.writeheader()
    for v in voters:
        writer.writerow(v.serialize())

