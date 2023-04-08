import os
import glob
import json
from dataclasses import dataclass, field
from collections import defaultdict
import string
import csv
import re
import argparse


@dataclass(kw_only=True)
class ContestSimple:
    id: int
    name: str
    choices: dict[int, str] = field(default_factory=dict)

    def to_dict(self, ranked_votes):
        assert not ranked_votes or ranked_votes.get(1) is not None
        votes = ranked_votes.get(1, [])
        assert len(votes) <= 1
        vote = votes[0] if len(votes) > 0 else None
        return {self.name: vote}

@dataclass
class ContestMultiple(ContestSimple):
    num_choices: int

    def to_dict(self, ranked_votes):
        assert not ranked_votes or ranked_votes.get(1) is not None
        votes = ranked_votes.get(1, [])
        ret = {}
        for i in range(self.num_choices):
            vote = votes[i] if i < len(votes) else None
            # using A/B/C/etc for choices so it's clear they're not ranked/ordered
            ret[f"{self.name}: CHOICE {string.ascii_uppercase[i]}"] = vote
        return ret

@dataclass
class ContestRanked(ContestSimple):
    num_ranks: int

    def _sanitize_ranked_votes(self, ranked_votes, simplify_rank=True):
        ret = {i: None for i in range(1, self.num_ranks + 1)}

        simplified_rank = 1
        for rank in range(1, self.num_ranks + 1):
            votes = ranked_votes.get(rank, [])
            if not votes:
                # this is an undervote for this rank, but apparently that's ok?
                continue

            if len(votes) != 1:
                # this ballot is now an overvote, STOP
                break

            if simplify_rank:
                ret[simplified_rank] = votes[0]
                simplified_rank += 1
            else:
                ret[rank] = votes[0]
        return ret

    def to_dict(self, ranked_votes):
        votes = self._sanitize_ranked_votes(ranked_votes)
        ret = {}
        for rank in range(1, self.num_ranks + 1):
            ret[f"{self.name}: RANK {rank}"] = votes[rank]
        return ret

@dataclass(kw_only=True)
class Vote:
    contest: ContestSimple | ContestMultiple | ContestRanked
    ranked_choices: dict[int, list[str]] = field(
        default_factory=lambda: defaultdict(list))

    def to_dict(self):
        return self.contest.to_dict(self.ranked_choices)

@dataclass
class VoterCard:
    precinct: str
    votes: list[Vote] = field(default_factory=list)

    def to_dict(self):
        ret = {"precinct": self.precinct}
        for vote in self.votes:
            ret.update(vote.to_dict())
        return ret

@dataclass(kw_only=True)
class BallotData:
    precinct_defs: dict[int, str] = field(default_factory=dict)
    ballot_defs: dict[int, ContestSimple | ContestMultiple | ContestRanked] = field(default_factory=dict)

    voter_cards: list[VoterCard] = field(default_factory=list)

    def get_fieldnames(self):
        ret = ['precinct']
        for b in self.ballot_defs.values():
            ret.extend(b.to_dict({}).keys())
        return ret


def get_ballot_data(input_dir):
    data = BallotData()

    # create a precinct index
    with open(os.path.join(input_dir, "PrecinctManifest.json")) as f:
        obj = json.load(f)

    for l in obj["List"]:
        # clean up precinct so that it is only a number
        pct = l["Description"]
        m = re.match(r"PCT (\d+)( MB)?", pct)
        assert m
        data.precinct_defs[l["Id"]] = m.group(1)

    # load all the vote contests into the ballot defs
    with open(os.path.join(input_dir, "ContestManifest.json")) as f:
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

        assert vote_def, "Unknown contest type"

        data.ballot_defs[vote_def.id] = vote_def

    # add all the choices to the ballot defs
    with open(os.path.join(input_dir, "CandidateManifest.json")) as f:
        obj = json.load(f)

    for l in obj["List"]:
        contest_id = l["ContestId"]
        data.ballot_defs[contest_id].choices[l["Id"]] = l["Description"]

    # read all the ballots
    paths = glob.glob(os.path.join(input_dir, "CvrExport*.json"))
    for p in paths:
        with open(p) as f:
            obj = json.load(f)

        for s in obj["Sessions"]:
            cvrs = [s["Original"], s.get("Modified", {})]
            cvrs = [x for x in cvrs if x.get("IsCurrent")]

            for cvr in cvrs:
                precinct_id = cvr["PrecinctPortionId"]
                for card in cvr["Cards"]:
                    voter = VoterCard(precinct=data.precinct_defs[precinct_id])
                    data.voter_cards.append(voter)
                    for contest in card["Contests"]:
                        vote = Vote(contest=data.ballot_defs[contest["Id"]])
                        voter.votes.append(vote)

                        for mark in contest["Marks"]:
                            if mark["IsVote"]:
                               candidate = vote.contest.choices[mark["CandidateId"]]
                               rank = mark["Rank"]
                               vote.ranked_choices[rank].append(candidate)

    return data


def mark_nones(d):
        return {k: (v if v is not None else "[-]") for k, v in d.items()}


def main():
    parser = argparse.ArgumentParser(
        description = "Converts a dump of unusable San Francisco Raw Ballot Data to usable CSV")
    parser.add_argument("input_dir")
    parser.add_argument("-o", "--output-csv-filename", default="voter_cards.csv")
    args = parser.parse_args()

    ballot_data = get_ballot_data(args.input_dir)

    with open(args.output_csv_filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ballot_data.get_fieldnames())
        writer.writeheader()
        for v in ballot_data.voter_cards:
            writer.writerow(mark_nones(v.to_dict()))

if __name__ == "__main__":
    main()
